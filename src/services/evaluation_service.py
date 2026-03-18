import json
import re
from typing import Any

import streamlit as st

from src.config.prompts import (
    CHECKLIST_SAMPLE_JSON,
    EVALUATION_CRITERIA,
    PROMPT as SOAP_GRADING_PROMPT,
    TRANSCRIPT_CHECKLIST_PROMPT,
)
from src.services.llm_service import llm_call


def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if "```" in text:
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _json_response_to_obj(response_json: dict[str, Any]) -> Any:
    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    content = _strip_code_fences(content)
    if not content:
        raise ValueError("Empty LLM response")
    return json.loads(content)


def _normalize_checklist_item(item: Any) -> dict[str, str]:
    if isinstance(item, str):
        return {
            "Question": item.strip(),
            "ExpectedAnswer": "",
            "Evaluated": "No",
            "Evidence": "",
        }

    if not isinstance(item, dict):
        return {
            "Question": str(item),
            "ExpectedAnswer": "",
            "Evaluated": "No",
            "Evidence": "",
        }

    return {
        "Question": str(item.get("Question") or item.get("question") or item.get("Objective") or "").strip(),
        "ExpectedAnswer": str(
            item.get("ExpectedAnswer")
            or item.get("expected_answer")
            or item.get("Answer")
            or item.get("objective")
            or ""
        ).strip(),
        "Evaluated": str(item.get("Evaluated") or item.get("evaluated") or item.get("status") or "No").strip() or "No",
        "Evidence": str(item.get("Evidence") or item.get("evidence") or item.get("Documented") or "").strip(),
    }


def _normalize_checklist_payload(payload: Any) -> list[dict[str, str]]:
    items = payload
    if isinstance(payload, dict):
        if isinstance(payload.get("questions_and_answers"), list):
            items = payload["questions_and_answers"]
        elif isinstance(payload.get("CheckList Evaluation"), list):
            items = payload["CheckList Evaluation"]
        else:
            items = []

    normalized = []
    for item in items or []:
        norm = _normalize_checklist_item(item)
        if norm["Question"]:
            normalized.append(norm)
    return normalized


def _normalize_grade_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "Assessment": "",
            "Possible CareScore": "",
            "Achieved CareScore": 0,
            "Objective": str(item),
            "Documented": "",
            "Non-Documented": "",
            "Improvement": "",
            "Achieved Score Reason": "",
        }

    return {
        "Assessment": item.get("Assessment") or item.get("assessment") or "",
        "Possible CareScore": item.get("Possible CareScore") or item.get("possible_score") or "",
        "Achieved CareScore": item.get("Achieved CareScore") or item.get("achieved_score") or 0,
        "Objective": item.get("Objective") or item.get("objective") or "",
        "Documented": item.get("Documented") or item.get("documented") or "",
        "Non-Documented": item.get("Non-Documented") or item.get("non_documented") or "",
        "Improvement": item.get("Improvement") or item.get("improvement") or "",
        "Achieved Score Reason": item.get("Achieved Score Reason") or item.get("achieved_score_reason") or "",
    }


def _coerce_score(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_grade_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    criteria = payload.get("criteria", [])
    if isinstance(criteria, dict):
        criteria = [criteria]

    normalized_criteria = [_normalize_grade_item(item) for item in criteria or []]
    top_criterion = normalized_criteria[0] if normalized_criteria else {}

    achieved_score = payload.get("achieved_score")
    if achieved_score in (None, ""):
        achieved_score = payload.get("Achieved CareScore")
    scored_criteria = [
        item for item in normalized_criteria
        if (_coerce_score(item.get("Achieved CareScore")) or 0) > 0
    ]
    matched_criterion = scored_criteria[0] if len(scored_criteria) == 1 else {}
    if achieved_score in (None, ""):
        achieved_score = matched_criterion.get("Achieved CareScore")
    if achieved_score in (None, ""):
        achieved_score = top_criterion.get("Achieved CareScore", 0)

    achieved_score_num = _coerce_score(achieved_score)

    selected_assessment = payload.get("assessment") or ""
    if not selected_assessment and achieved_score_num is not None and normalized_criteria:
        # Pick the criterion whose score bucket contains the achieved score.
        for item in normalized_criteria:
            possible = str(item.get("Possible CareScore", "")).strip()
            assessment_name = item.get("Assessment", "")
            if not possible or not assessment_name:
                continue
            if possible.startswith("<"):
                try:
                    threshold = float(possible.replace("<", "").strip())
                    if achieved_score_num < threshold:
                        selected_assessment = assessment_name
                        break
                except ValueError:
                    continue
            elif "-" in possible:
                try:
                    low_text, high_text = possible.split("-", 1)
                    low = float(low_text.strip())
                    high = float(high_text.strip())
                    if low <= achieved_score_num <= high:
                        selected_assessment = assessment_name
                        break
                except ValueError:
                    continue

    if not matched_criterion and selected_assessment:
        for item in normalized_criteria:
            if str(item.get("Assessment", "")).strip().lower() == selected_assessment.strip().lower():
                matched_criterion = item
                break

    matched_score = _coerce_score((matched_criterion or {}).get("Achieved CareScore"))
    if matched_score is not None and (achieved_score_num is None or achieved_score_num <= 0):
        achieved_score = matched_criterion.get("Achieved CareScore")
        achieved_score_num = matched_score

    if not selected_assessment:
        selected_assessment = top_criterion.get("Assessment", "")

    total_possible_score = payload.get("total_possible_score") or payload.get("Total CareScore") or ""
    if not total_possible_score and matched_criterion:
        total_possible_score = matched_criterion.get("Possible CareScore", "")
    if not total_possible_score:
        total_possible_score = top_criterion.get("Possible CareScore", "")

    return {
        "criteria": normalized_criteria,
        "assessment": selected_assessment,
        "achieved_score": achieved_score,
        "total_possible_score": total_possible_score,
        "evaluation_summary": payload.get("evaluation_summary") or "",
        "detailed_llm_reasoning": payload.get("detailed_llm_reasoning") or "",
    }


def _serialize_soap_for_grading(soap_data: dict[str, Any] | None) -> str:
    if not isinstance(soap_data, dict):
        return ""
    return json.dumps(soap_data, indent=2, ensure_ascii=False)


def _grade_from_inputs(soap_text: str, transcript: str = "") -> dict[str, Any]:
    prompt = "\n\n".join([
        "You are a clinician grading a student's final SOAP note.",
        SOAP_GRADING_PROMPT,
        "Evaluation Criteria JSON:\n" + EVALUATION_CRITERIA,
        "Interview Transcript:\n" + (transcript or ""),
        "Final SOAP Note:\n" + (soap_text or ""),
        "Return ONLY valid JSON.",
    ])

    response_json = llm_call(
        model=st.session_state.get("gemini_model", "gemini-3-pro-preview"),
        messages=[
            {"role": "system", "content": "Grade the final SOAP note against the case file."},
            {"role": "user", "content": prompt},
        ],
        format="json",
    )
    if not response_json:
        return {}

    try:
        payload = _json_response_to_obj(response_json)
        return _normalize_grade_payload(payload)
    except Exception as exc:
        st.warning(f"SOAP grading failed: {exc}")
        return {}


def generate_checklist(transcript: str) -> list[dict[str, str]]:
    if not (transcript or "").strip():
        return []

    prompt = "\n\n".join([
        "You are a clinician evaluating an encounter transcript.",
        TRANSCRIPT_CHECKLIST_PROMPT,
        "Transcript:\n" + transcript,
        "Checklist JSON sample:\n" + CHECKLIST_SAMPLE_JSON,
    ])

    response_json = llm_call(
        model=st.session_state.get("gemini_model", "gemini-3-pro-preview"),
        messages=[
            {"role": "system", "content": "Create and evaluate a checklist directly from the transcript."},
            {"role": "user", "content": prompt},
        ],
        format="json",
    )
    if not response_json:
        return []

    try:
        payload = _json_response_to_obj(response_json)
        return _normalize_checklist_payload(payload)
    except Exception as exc:
        st.warning(f"Checklist generation failed: {exc}")
        return []


def generate_checklist_artifact(transcript: str) -> list[dict[str, str]]:
    return generate_checklist(transcript)


def grade_soap_note(transcript: str, soap_data: dict[str, Any] | None) -> dict[str, Any]:
    soap_text = _serialize_soap_for_grading(soap_data)
    return _grade_from_inputs(soap_text, transcript)


def grade_final_soap_note(soap_text: str, transcript: str = "") -> dict[str, Any]:
    if not (soap_text or "").strip():
        return {}
    return _grade_from_inputs(soap_text, transcript)


def checklist_counts(checklist: list[dict[str, str]]) -> dict[str, int]:
    counts = {"Yes": 0, "No": 0, "Partial": 0}
    for item in checklist or []:
        status = str(item.get("Evaluated", "")).strip().title()
        if status not in counts:
            status = "No"
        counts[status] += 1
    return counts
