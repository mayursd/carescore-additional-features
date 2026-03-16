import time
import logging
import streamlit as st
import google.generativeai as genai
from src.config.prompts import AUDIO_TRANSCRIPT_PROMPT, VIDEO_TRANSCRIPT_PROMPT, TRANSCRIPT_NOTE_PROMPT
from src.services.llm_service import llm_call
from src.services.soap_service import remove_student_name


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioVideoToNoteGenerator:

    def __init__(self):
        self.generation_config = {
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

    def prepare_note_messages(self, interview):
        return [
            {'role': 'system',
             'content': 'You are a clinician in Medical hospital. You summarize the interview with patient to patient note.'},
            {'role': 'user', 'content': TRANSCRIPT_NOTE_PROMPT},
            {'role': 'user', 'content': 'Interview: \n' + interview},
        ]

    def generate_note(self, uploaded_file, mime_type):
        # Debug: Check API key
        api_key = st.session_state.get('gemini_ai_key')
        if not api_key:
            raise ValueError("Gemini AI API key not found in session state")
        
        genai.configure(api_key=api_key)

        import os
        logger.info("Uploading file with MIME type: %s", mime_type)
        if isinstance(uploaded_file, str):  # File path
            file_size = os.path.getsize(uploaded_file) if os.path.exists(uploaded_file) else 0
        
        try:
            # Upload the file (exactly like evaluation page)
            file = genai.upload_file(uploaded_file, mime_type=mime_type)
            
            # Wait until it becomes ACTIVE (exactly like evaluation page)
            while file.state.name == "PROCESSING":
                time.sleep(5)
                file = genai.get_file(file.name)

            if file.state.name != "ACTIVE":
                st.error(f"File processing failed or timed out. State: {file.state.name}")
                # Clean up the file
                try:
                    genai.delete_file(file.name)
                except:
                    pass
                return None

            # Generate transcript using selectable model (defaults if invalid)
            selected_gemini = st.session_state.get('gemini_model', 'gemini-3-flash-preview')
            try:
                model = genai.GenerativeModel(selected_gemini)
            except Exception:
                st.warning(f"Invalid Gemini model '{selected_gemini}', falling back to gemini-3-flash-preview")
                model = genai.GenerativeModel('gemini-3-flash-preview')
            
            # Use VIDEO_TRANSCRIPT_PROMPT for video files (like evaluation page)
            if mime_type == "video/mp4":
                transcript_prompt = VIDEO_TRANSCRIPT_PROMPT
            else:
                transcript_prompt = AUDIO_TRANSCRIPT_PROMPT
            
            try:
                logger.info("Generating transcript with Gemini model: %s", selected_gemini)
                response = model.generate_content(
                    [transcript_prompt, file],
                    generation_config={"temperature": 0.2},
                    # request_options={"timeout": 300}
            
                )

                
            except Exception as gemini_error:
                st.error(f"❌ Gemini API call failed: {str(gemini_error)}")
                raise gemini_error
            
            logger.info(f"Gemini response {str(response)}")
            # Delete the file after processing (like evaluation page)
            try:
                genai.delete_file(file.name)
            except:
                pass
            logger.info("Transcript generation response received")
            transcript = response.text.strip()
         
            
            # Remove student name if filename contains it
            file_name = getattr(uploaded_file, 'name', str(uploaded_file))
            if isinstance(uploaded_file, str):
                file_name = os.path.basename(uploaded_file)
            
            cleaned_interview = remove_student_name(transcript, file_name)
            
            # Generate note from cleaned interview
            note_messages = self.prepare_note_messages(cleaned_interview)
            
            interview_note = llm_call(
                model=st.session_state.get('gemini_model', 'gemini-3-flash-preview'),
                messages=note_messages
            )
            
            # Return structured data that UI expects
            return {
                "interview": cleaned_interview,
                "summary": interview_note.get("choices", [{}])[0].get("message", {}).get("content", "Summary generation failed"),
                "transcript": cleaned_interview,  # Legacy compatibility
                "note": interview_note.get("choices", [{}])[0].get("message", {}).get("content", "Note generation failed")
            }

        except Exception as e:
            st.error(f"Error processing audio/video file: {str(e)}")
            # Clean up the file if it exists
            if 'file' in locals():
                try:
                    genai.delete_file(file.name)
                except:
                    pass
            return None

    def get_transcript(self, file, model, transcript_prompt, retry_count=0):
        try:
            response = model.generate_content(contents=[transcript_prompt, file],
                                            generation_config=self.generation_config)
        except Exception as e:
            error_message = str(e)
            if error_message.__contains__("ACTIVE state") \
                    and error_message.__contains__("usage") \
                    and error_message.__contains__("not allowed"):
                time.sleep(10)
                if retry_count < 9:
                    return self.get_transcript(file, model, transcript_prompt, retry_count=retry_count+1)
                else:
                    raise e
        return response
