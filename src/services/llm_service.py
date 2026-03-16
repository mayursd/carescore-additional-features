import json
import os
import re
import time
import random
from typing import Any, Optional

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.config.prompts import SOAP_ASSESSMENT_PLAN_SUGGESTION_PROMPT


def _get_gemini_api_key() -> str:
    key = (st.session_state.get("gemini_ai_key") or os.environ.get("GEMINI_AI_KEY") or "").strip()
    if key:
        st.session_state.gemini_ai_key = key
    return key


def _normalize_gemini_model(model: Optional[str]) -> str:
    model = (model or "").strip()
    if not model:
        model = (st.session_state.get("gemini_model") or "gemini-3-pro-preview").strip()
    if model.startswith("google/"):
        model = model.split("/", 1)[1]
    return model or "gemini-3-pro-preview"


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for msg in messages or []:
        role = (msg.get("role") or "user").strip()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            chunks.append(f"System:\n{content}")
        elif role == "assistant":
            chunks.append(f"Assistant:\n{content}")
        else:
            chunks.append(f"User:\n{content}")
    return "\n\n".join(chunks).strip()


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if "```" in t:
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()

def llm_call(model, messages, format=None):
    """Gemini-only LLM call.

    Returns an OpenAI-style dict for backwards compatibility:
    {"choices": [{"message": {"content": "..."}}]}
    """

    api_key = _get_gemini_api_key()
    if not api_key:
        st.error("❌ Gemini API key not configured (set GEMINI_AI_KEY).")
        return None

    model_name = _normalize_gemini_model(model)
    prompt = _messages_to_prompt(messages)

    if format == "json":
        prompt = prompt + "\n\nReturn ONLY a valid JSON object (no markdown, no code fences, no commentary)."

    generation_config: dict[str, Any] = {
        "temperature": 0.3,
        "top_p": 0.9,
        "top_k": 50,
    }
    if format == "json":
        generation_config["response_mime_type"] = "application/json"

    def is_quota_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        # Typical messages: "429 Resource has been exhausted" / "resource_exhausted" / "rate limit"
        return (
            "429" in msg
            or "resource has been exhausted" in msg
            or "resource_exhausted" in msg
            or "rate limit" in msg
            or "quota" in msg
        )

    max_attempts = int(os.environ.get("GEMINI_MAX_ATTEMPTS", "4") or "4")
    base_delay_s = float(os.environ.get("GEMINI_RETRY_BASE_SECONDS", "1.0") or "1.0")
    fallback_model = (os.environ.get("GEMINI_FALLBACK_MODEL") or "").strip()
    if not fallback_model and "pro" in model_name:
        # Reasonable default when Pro hits quota
        fallback_model = "gemini-3-flash-preview"

    last_exc: Optional[Exception] = None

    genai.configure(api_key=api_key)

    for attempt in range(1, max_attempts + 1):
        try:
            gemini_model = genai.GenerativeModel(model_name)
            response = gemini_model.generate_content(prompt, generation_config=generation_config)
            content = (getattr(response, "text", None) or "").strip()
            return {"choices": [{"message": {"content": content}}]}
        except Exception as e:
            last_exc = e
            if not is_quota_error(e) or attempt == max_attempts:
                break

            # Exponential backoff with jitter
            delay = base_delay_s * (2 ** (attempt - 1))
            delay = delay + random.uniform(0.0, min(0.5, delay * 0.25))
            time.sleep(delay)

    # Optional single fallback attempt if we kept hitting quota
    if last_exc and is_quota_error(last_exc) and fallback_model and fallback_model != model_name:
        try:
            gemini_model = genai.GenerativeModel(_normalize_gemini_model(fallback_model))
            response = gemini_model.generate_content(prompt, generation_config=generation_config)
            content = (getattr(response, "text", None) or "").strip()
            return {"choices": [{"message": {"content": content}}]}
        except Exception as e:
            last_exc = e

    st.error(
        "❌ Gemini API call failed: quota/rate limit exceeded. "
        "Try again in ~30–120s, or switch to a Flash model / raise quota. "
        f"Details: {str(last_exc)}"
    )
    return None

def generate_soap_suggestions(transcript, current_ap_data, case_file_content=""):
    prompt = SOAP_ASSESSMENT_PLAN_SUGGESTION_PROMPT.format(
        transcript=transcript,
        current_ap_data=json.dumps(current_ap_data, indent=2),
        case_file_content=case_file_content
    )

    selected_model = st.session_state.get('gemini_model', 'gemini-3-pro-preview')
    response_json = llm_call(
        model=selected_model,
        messages=[
            {"role": "system", "content": "You are an expert clinician."},
            {"role": "user", "content": prompt},
        ],
        format="json",
    )
    if not response_json:
        return {}

    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    content = _strip_code_fences(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        st.error(f"Error decoding AI suggestions JSON: {e}")
        return {}


def process_interview(audio_file):
    """
    Process interview file and return SOAP note generation results
    
    Args:
        audio_file: BytesIO object containing audio/video file
        
    Returns:
        dict: Contains soap_note and transcript
    """
    try:
        # Import here to avoid circular imports
        from src.utils.file_utils import get_file_content
        
        # Extract content from audio file
        interview_content = get_file_content(audio_file)
        
        if not interview_content:
            raise Exception("Failed to extract content from audio file")
        
        # Extract transcript text (this is what we actually need for processing)
        transcript = ""
        if isinstance(interview_content, dict):
            transcript = interview_content.get('transcript', interview_content.get('interview', str(interview_content)))
        else:
            transcript = str(interview_content)
        
        if not transcript.strip():
            raise Exception("No transcript content found")
        
        # Generate SOAP note from transcript
        soap_note = generate_soap_note(transcript)

        print(soap_note)
        
        return {
            'soap_note': soap_note,
            'transcript': transcript
        }
        
    except Exception as e:
        st.error(f"Error processing interview: {str(e)}")
        return {
            'soap_note': '',
            'transcript': ''
        }


def generate_soap_note(transcript):
    """Generate SOAP note from transcript content"""
    try:
        # Create context for SOAP generation using the cleaned transcript
        context = f"Interview Transcript:\n{transcript}\n\n"
        
        # Generate SOAP note using AI
        soap_messages = [
            {
                "role": "system", 
                "content": "You are a medical AI assistant. Generate a comprehensive SOAP note based on the provided interview transcript. Format it clearly with Subjective, Objective, Assessment, and Plan sections."
            },
            {
                "role": "user", 
                "content": context
            }
        ]
        
        selected_model = st.session_state.get('gemini_model', 'gemini-3-pro-preview')
        soap_response = llm_call(
            model=selected_model,
            messages=soap_messages,
        )
        
        if soap_response and "choices" in soap_response:
            return soap_response["choices"][0]["message"]["content"]
        else:
            return "Failed to generate SOAP note"
            
    except Exception as e:
        st.error(f"Failed to generate SOAP note: {str(e)}")
        return ""