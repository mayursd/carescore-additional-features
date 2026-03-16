"""
Processing Pipeline Components
Contains components for automated processing workflows
"""
import os
import logging
import streamlit as st
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from src.services.evaluation_service import generate_checklist_artifact
from src.services.llm_service import process_interview


logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def render(self):
        """Render the automated processing pipeline"""
        if not st.session_state.get('interview_file'):
            st.error("❌ No interview file available")
            return
            
        interview_file = st.session_state.interview_file
        
        st.markdown("### 🤖 Automated Processing Pipeline")
        st.info("ℹ️ Ready to generate SOAP note from interview audio")
        # Auto-start: switch to dedicated processing stage so recording UI hides
        if not st.session_state.get('processing_started') and not st.session_state.get('soap_data'):
            st.session_state.processing_started = True
            st.session_state.workflow_stage = 'processing'
            st.rerun()
            return
        # If already complete (soap_data present) we don't render anything special here
        if st.session_state.get('soap_data'):
            st.success("✅ Processing complete.")
        else:
            st.info("⏳ Processing queued...")
    
    def run_processing_pipeline(self, interview_file):
        """Run the automated processing pipeline"""
        st.markdown("### 🔄 Processing Interview...")
        
        # Basic validation so we fail fast before invoking downstream services.
        if interview_file is None:
            st.error("❌ No interview file provided.")
            st.session_state.processing_inflight = False
            st.session_state.processing_started = False
            return

        file_size = None
        try:
            if isinstance(interview_file, str):
                if os.path.exists(interview_file):
                    file_size = os.path.getsize(interview_file)
                else:
                    file_size = 0
            elif hasattr(interview_file, "size"):
                file_size = getattr(interview_file, "size", None)
            elif hasattr(interview_file, "getbuffer"):
                file_size = len(interview_file.getbuffer())
            elif hasattr(interview_file, "seek") and hasattr(interview_file, "tell"):
                current_pos = interview_file.tell()
                interview_file.seek(0, os.SEEK_END)
                file_size = interview_file.tell()
                interview_file.seek(current_pos)
        except Exception:
            file_size = None

        if file_size is not None and file_size <= 0:
            st.error("❌ Uploaded interview file appears to be empty.")
            st.session_state.processing_inflight = False
            st.session_state.processing_started = False
            return

        # Clear any cached processing results to ensure fresh start
        for key in [
            'interview_content',
            'transcription_result',
            'auto_checklist',
            'student_grade',
            'case_file',
            'case_file_content',
            'case_file_signature',
            'case_title',
            'final_soap_text',
            'final_soap_signature',
            'final_soap_name',
            'final_soap_upload',
        ]:
            st.session_state.pop(key, None)

        total_steps = 4
        
        # Progress bar and status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Transcribe audio (ALWAYS run this step)
            status_text.text(f"🎧 Step 1/{total_steps}: Transcribing audio...")
            progress_bar.progress(int(100 / total_steps))
            # print user and datetime
            user_info = st.session_state.get('user') or {}
            username = user_info.get('username') or 'unknown'
            logger.info("[Processing] User: %s", username)
            try:
                now_chicago = datetime.now(ZoneInfo("America/Chicago"))
                logger.info(
                    "[Processing] Start time (America/Chicago): "
                    f"{now_chicago.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            except Exception:
                # Fallback to local time if zoneinfo not available for any reason
                logger.info(
                    "[Processing] Start time (local fallback): "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                )
            from src.utils.file_utils import get_file_content
            st.session_state.interview_content = get_file_content(interview_file)
            logger.info("[Processing] Interview content retrieved.")
            logger.info(
                "[Processing] Interview content length: "
                f"{len(str(st.session_state.interview_content))}"
            )
            if(len(str(st.session_state.interview_content))==0):
                st.error("❌ Transcription returned empty content.")
            # Store transcript for display in results
            if isinstance(st.session_state.interview_content, dict):
                st.session_state.transcript = st.session_state.interview_content.get("interview", "")
            else:
                st.session_state.transcript = str(st.session_state.interview_content)

            current_step = 2
            status_text.text(f"📄 Step {current_step}/{total_steps}: Generating SOAP note...")
            progress_bar.progress(int((current_step / total_steps) * 100))
            
            self.generate_automated_soap()
            logger.info("[Processing] SOAP data generated.")

            current_step += 1
            status_text.text(f"📋 Step {current_step}/{total_steps}: Running checklist...")
            progress_bar.progress(int((current_step / total_steps) * 100))
            try:
                st.session_state.auto_checklist = generate_checklist_artifact(
                    st.session_state.get("transcript", ""),
                )
            except Exception as exc:
                logger.warning("[Processing] Checklist generation failed: %s", exc)
                st.warning(f"Checklist generation failed: {exc}")
                st.session_state.auto_checklist = []

            # Final step: Complete
            status_text.text(f"✅ Step {total_steps}/{total_steps}: Analysis complete!")
            progress_bar.progress(100)
            
            st.session_state.workflow_stage = "results_ready"
            st.session_state.processing_complete = True
            st.session_state.processing_inflight = False
            st.session_state.processing_retry_count = 0
            st.success("🎉 Interview processed successfully!")
            time.sleep(1.5)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Processing failed: {str(e)}")
            progress_bar.progress(0)
            status_text.text("❌ Processing failed")
            st.session_state.processing_inflight = False
            st.session_state.processing_started = False
            st.session_state.processing_retry_count = 0
            st.session_state.workflow_stage = "audio_input"
    
    def generate_automated_soap(self):
        """Generate SOAP note using the same pattern as the backup file, now precomputes AI plan and DOCX bytes"""
        try:
            # Clear any cached SOAP results
            for key in ['soap_data', 'soap_result', 'soap_generation_debug', 'soap_docx_bytes', 'ai_plan']:
                if key in st.session_state:
                    del st.session_state[key]
                
            if not st.session_state.get('interview_content'):
                st.error("❌ No interview content available.")
                return None

            # Handle both string and dictionary formats
            if isinstance(st.session_state.interview_content, dict):
                interview_text = st.session_state.interview_content["interview"]
            else:
                interview_text = str(st.session_state.interview_content)
                
            # Extract SOAP data for display
            from src.services.soap_service import extract_soap_data
            soap_response = extract_soap_data(interview_text)
            
            if soap_response and "soap_data" in soap_response:
                st.session_state.soap_data = soap_response["soap_data"]
                st.success("✅ SOAP note generated successfully!")
            else:
                st.warning("⚠️ Structured SOAP extraction failed. Attempting fallback generation.")
                fallback = self._fallback_build_basic_soap(interview_text)
                if fallback:
                    st.session_state.soap_data = fallback
                    st.session_state.soap_fallback = True
                    st.info("Generated minimal SOAP note from transcript (fallback).")
                else:
                    st.error("❌ Failed to extract or synthesize SOAP data.")
                    return None

            # --- Step 2: Generate AI Assessment & Plan (precompute) ---
            from src.services.soap_service import generate_ai_assessment_plan, _normalize_ap_dict
            from src.ui.components.results_display import _build_docx_bytes_cached, SoapNoteDisplay, _format_ai_plan_text

            ap_norm = _normalize_ap_dict(st.session_state.soap_data.get("Assessment_Plan"))
            transcript_txt = interview_text.strip()

            #  Precompute AI plan
            if transcript_txt:
                ai_dict = generate_ai_assessment_plan(transcript_txt, ap_norm) or {}
                ai_text = _format_ai_plan_text(ai_dict) if ai_dict else ""
            else:
                ai_text = "\n".join([
                    "Final diagnosis or problems(s): Not documented",
                    "Investigations: Not documented",
                    "Medications: Not documented",
                    "Education: Not documented",
                    "Follow-Up: Not documented",
                    "Referrals/Consults: Not documented",
                    "Disposition: Not documented",
                    "Other: Not documented",
                ])

            st.session_state["ai_plan"] = ai_text
            ap = st.session_state.soap_data.get("Assessment_Plan") or {}
            ap["AI_Plan"] = ai_text
            st.session_state.soap_data["Assessment_Plan"] = ap

            # --- Step 3: Pre-build DOCX bytes for instant download ---
            template_path = "src/templates/SOAP_Note_Template.docx"
            soap_note_text = SoapNoteDisplay()._generate_full_soap_text(st.session_state.soap_data)
            st.session_state["soap_docx_bytes"] = _build_docx_bytes_cached(
                soap_text=soap_note_text,
                interview_text=transcript_txt,
                template_path=template_path
            )

            return "SOAP_DATA_PRECOMPUTED"

        except Exception as e:
            st.error(f"❌ Failed to generate SOAP note: {str(e)}")
            st.session_state.soap_generation_debug = {"error": str(e)}
            return None

    def _fallback_build_basic_soap(self, transcript: str):
        """Create a minimal SOAP structure if LLM JSON extraction fails.

        This prevents a total block in the UI and allows user editing.
        """
        try:
            snippet = (transcript or "").strip().split('\n')
            first_lines = '\n'.join(snippet[:40])  # rough HPI approximation

            return {
                "HPI": first_lines[:1500] or "Not mentioned",
                "PMHx": "Not mentioned",
                "FHx": "Not mentioned",
                "SHx": {
                    "Tobacco": "Not mentioned",
                    "ETOH": "Not mentioned",
                    "Drugs": "Not mentioned",
                    "Diet": "Not mentioned",
                    "Exercise": "Not mentioned",
                    "Sexual_activity": "Not mentioned",
                    "Occupation": "Not mentioned",
                    "Living_situation": "Not mentioned",
                    "Safety": "Not mentioned",
                },
                "Medications": "Not mentioned",
                "Allergies": "Not mentioned",
                "Review_of_Systems": {
                    "General": "Not mentioned",
                    "Eyes": "Not mentioned",
                    "ENT": "Not mentioned",
                    "Cardiovascular": "Not mentioned",
                    "Respiratory": "Not mentioned",
                    "Gastrointestinal": "Not mentioned",
                    "Genitourinary": "Not mentioned",
                    "Musculoskeletal": "Not mentioned",
                    "Neurological": "Not mentioned",
                    "Psychiatric": "Not mentioned",
                    "Integument": "Not mentioned",
                    "Endocrine": "Not mentioned",
                    "Hematopoietic_Lymphatic": "Not mentioned",
                    "Allergy_Immunology": "Not mentioned",
                },
                "Objective": {
                    "General_Appearance": "Not mentioned",
                    "HEENT": "Not mentioned",
                    "Neck": "Not mentioned",
                    "Cardiovascular": "Not mentioned",
                    "Pulmonary": "Not mentioned",
                    "GI_Abdomen": "Not mentioned",
                    "GU": "Not mentioned",
                    "Musculoskeletal": "Not mentioned",
                    "Neurological": "Not mentioned",
                    "Psychiatric": "Not mentioned",
                    "Integument": "Not mentioned",
                },
                "Assessment_Plan": {
                    "Final_diagnosis": "Not determined (fallback)",
                    "Investigations": "Need full AI extraction to populate",
                    "Medications": "Not mentioned",
                    "Consults": "Not mentioned",
                    "Disposition": "Not mentioned",
                    "Pt_Education": "Not mentioned",
                    "Other": "Not mentioned"
                }
            }
        except Exception as e:
            st.session_state.soap_generation_debug = {"fallback_error": str(e)}
            return None
