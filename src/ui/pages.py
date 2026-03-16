"""
Streamlined Pages Module - Modular Version
Main UI orchestrator using extracted components
"""
import os
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from .components import (
    ChecklistDisplay,
    LiveRecorder,
    FileUploader,
    GradeDisplay,
    RecordingRetrieval,
    ProcessingPipeline,
    SoapNoteDisplay,
    TranscriptDisplay,
    ResultsSummary,
)


class SessionState:
    def __init__(self):
        if "gemini_ai_key" not in st.session_state:
            st.session_state.gemini_ai_key = os.environ.get("GEMINI_AI_KEY", "")
        if "daily_api_key" not in st.session_state:
            st.session_state.daily_api_key = os.environ.get("DAILY_API_KEY", "")
        if "soap_note_file" not in st.session_state:
            st.session_state.soap_note_file = None
        if "soap_data" not in st.session_state:
            st.session_state.soap_data = None
        if "case_title" not in st.session_state:
            st.session_state.case_title = ""
        if "auto_checklist" not in st.session_state:
            st.session_state.auto_checklist = []
        if "student_grade" not in st.session_state:
            st.session_state.student_grade = {}
        if "final_soap_text" not in st.session_state:
            st.session_state.final_soap_text = ""


class Page:
    def render(self):
        pass


class StreamlinedWorkflowPage(Page):
    MAX_PROCESSING_RETRIES = 4

    def __init__(self):
        self.live_recorder = LiveRecorder()
        self.file_uploader = FileUploader()
        self.recording_retrieval = RecordingRetrieval()
        self.processing_pipeline = ProcessingPipeline()
        self.checklist_display = ChecklistDisplay()
        self.grade_display = GradeDisplay()
        self.soap_display = SoapNoteDisplay()
        self.transcript_display = TranscriptDisplay()
        self.results_summary = ResultsSummary()
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'workflow_stage': 'audio_input',  # Start directly at audio input
            'interview_file': None,
            'soap_note': '',
            'transcript': '',
            'room_name': '',
            'downloading_recording': False,
            'current_recording': None,
            'auto_checklist': [],
            'student_grade': {},
            'final_soap_text': '',
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def render(self):
        """Main render method"""
    # (Debug & model settings moved into Navigation advanced section)

        # Main content area
        
        # Header with dual logos and clear purpose
        self._render_header_with_logos()
        
    def _render_header_with_logos(self):
        """Render header with LOF and RFU logos - equal size and spacing"""
        # Add custom CSS for perfect logo alignment
        st.markdown("""
        <style>
        .logo-container {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            height: 100px;
        }
        .logo-container img {
            max-height: 80px !important;
            max-width: 120px !important;
            width: auto !important;
            height: auto !important;
            object-fit: contain;
        }
        .center-content {
            text-align: center;
            padding: 20px 40px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        header_col1, header_col2, header_col3 = st.columns([0.5, 2, 0.5])
        
        with header_col1:
            # LOF Logo (left) with equal sizing
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            lof_logo_path = "src/ui/assets/lof_logo.png"
            if os.path.exists(lof_logo_path):
                st.image(lof_logo_path, width=150)
            else:
                st.markdown('<div style="text-align: center;">🦋 **Leap of Faith**</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with header_col2:
            # CareScore AI centered with better spacing
            st.markdown("""
            <div class="center-content">
                <h1 style='color: #2E8B57; margin-right: 100px; font-size: 2.5rem;'>🏥 CareScore AI</h1>
                <p style='color: #666; margin: 8px 0; margin-right:100px; font-size: 1.1rem;'>🩺 Transforming Clinical Conversations into Structured Documentation</p>
            </div>
            """, unsafe_allow_html=True)
        
        with header_col3:
            # RFU Logo (right) with equal sizing and spacing
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            rfu_logo_path = "src/ui/assets/rfu_logo.png"
            if os.path.exists(rfu_logo_path):
                st.image(rfu_logo_path, width=130)
            else:
                st.markdown('<div style="text-align: center;">**🎓 RFU**</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Show simple progress without complex navigation
        self._render_simple_progress()
        
        # Route to appropriate stage
        stage = st.session_state.get('workflow_stage', 'audio_input')
        
        # Force audio_input if no interview file exists
        if stage != 'audio_input' and not st.session_state.get('interview_file'):
            st.warning("⚠️ No audio file found, returning to audio input stage")
            st.session_state.workflow_stage = 'audio_input'
            stage = 'audio_input'
            st.rerun()
        
        if stage == 'audio_input':
            self._render_audio_input_stage()
        elif stage == 'processing':
            self._render_processing_stage()
        elif stage == 'results_ready':
            self._render_results_stage()
        else:
            st.error(f"Unknown workflow stage: {stage}")
            if st.button("🔄 Start Over", type="primary"):
                self._reset_workflow()
    
    def _render_simple_progress(self):
        """Render simplified progress indicator"""
        stage = st.session_state.workflow_stage
        
        # Create a simple progress bar
        if stage == 'audio_input':
            if st.session_state.get('interview_file'):
                # Audio chosen; ready to process (single-step workflow)
                progress = 0.66
                status = "Step 2: Generate SOAP Note"
            else:
                progress = 0.33
                status = "Step 1: Choose Audio Source"
        elif stage == 'processing':
            progress = 0.90
            status = "Processing..."
        elif stage == 'results_ready':
            progress = 1.0
            status = "Step 3: View Results"
        else:
            progress = 0.0
            status = "Getting Started"
        
        st.progress(progress)
        st.markdown(f"**{status}**")
        st.markdown("---")
    
    def _render_audio_input_stage(self):
        """Render the audio input stage - simplified"""
        st.markdown("## 🎙️ Step 1: Provide Your Interview Audio")
        st.markdown("Choose the easiest option for you:")
        
        if st.session_state.get('retry_limit_reached'):
            st.error(
                f"❌ Maximum retry attempts ({self.MAX_PROCESSING_RETRIES}) reached. Please check your network connection and restart the processing when you're ready."
            )
            del st.session_state['retry_limit_reached']

        processing_active = (
            st.session_state.get('processing_started')
            and not st.session_state.get('soap_data')
            and st.session_state.get('interview_file') is not None
        )
        if not processing_active:
            # Show acquisition tabs only while not processing
            tab1, tab2, tab3 = st.tabs(["🎥 Record Live", "☁️ Get Recording", "📁 Upload File"])
            with tab1:
                st.markdown("### Record Live Interview")
                st.markdown("*Best for: Real-time clinical interviews*")
                self.live_recorder.render()
            with tab2:
                st.markdown("### Retrieve a Previous Recording")
                st.markdown("*Best for: Accessing a recording you made earlier*")
                self.recording_retrieval.render()
            with tab3:
                st.markdown("### Upload an Audio/Video File")
                st.markdown("*Best for: Pre-recorded interviews on your device*")
                self.file_uploader.render(self._on_file_upload_analysis)
        else:
            st.info("🔄 Processing started – recording inputs hidden.")
        
        # Simple navigation - only show what's relevant
        st.markdown("---")

        # If audio is ready and processing not started, show pipeline trigger component
        if st.session_state.get('interview_file') and not processing_active:
            st.markdown("### Ready to generate your SOAP note?")
            st.info("🤖 Our AI will analyze the interview and create a professional SOAP note. This usually takes 1-3 minutes.")
            self.processing_pipeline.render()
        # Show results if available
        elif st.session_state.get('soap_data') or st.session_state.get('transcript'):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("📊 View Previous Results", use_container_width=True):
                    st.session_state.workflow_stage = 'results_ready'
                    st.rerun()
        
    # _render_audio_ready_stage removed (merged into audio_input stage)
    
    def _render_processing_stage(self):
        """Render processing stage - more engaging"""
        st.markdown("## 🤖 AI Analysis in Progress")
        st.info("⏱️ This usually takes 1-3 minutes. Please wait...")
        # Always require an interview file before proceeding.
        interview_file = st.session_state.get('interview_file')
        if not interview_file:
            st.error("Interview file missing; returning to start")
            st.session_state.workflow_stage = 'audio_input'
            st.rerun()
            return

        processing_artifact_keys = [
            'interview_content',
            'transcription_result',
            'transcript',
            'soap_data',
            'soap_result',
            'soap_generation_debug',
            'auto_checklist',
            'student_grade',
        ]

        # If we re-enter processing with prior results, clear them so we regenerate fresh output.
        if st.session_state.get('soap_data'):
            for key in processing_artifact_keys:
                if key in st.session_state:
                    del st.session_state[key]

        if not st.session_state.get('processing_inflight'):
            st.session_state.processing_inflight = True
            st.session_state.processing_retry_count = 0
        else:
            st.session_state.processing_retry_count = st.session_state.get('processing_retry_count', 0) + 1
            if st.session_state.processing_retry_count >= self.MAX_PROCESSING_RETRIES:
                st.session_state.retry_limit_reached = True
                st.session_state.processing_inflight = False
                st.session_state.processing_started = False
                st.session_state.workflow_stage = 'audio_input'
                if 'interview_file' in st.session_state:
                    del st.session_state['interview_file']
                for key in processing_artifact_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.pop('processing_retry_count', None)
                st.rerun()
                return
            st.info(
                f"🔄 Connection hiccup detected. Please check your network connection. Retrying processing (attempt {st.session_state.processing_retry_count})."
            )
            # Clear any in-progress artifacts so the rerun starts fresh.
            for key in processing_artifact_keys:
                if key in st.session_state:
                    del st.session_state[key]

        with st.spinner("Analyzing interview..."):
            self.processing_pipeline.run_processing_pipeline(interview_file)

        st.session_state.processing_inflight = False
    
    def _render_results_stage(self):
        """Render results stage - improved layout"""
        st.markdown("## 🎯 Step 3: Your SOAP Note is Ready!")

        # Results summary - simplified
        self.results_summary.render()

        tab_labels = ["📄 SOAP Note", "📝 Transcript"]
        tab_renderers = [self.soap_display.render, self.transcript_display.render]

        if st.session_state.get("auto_checklist"):
            tab_labels.append("📋 Checklist")
            tab_renderers.append(self.checklist_display.render)

        if st.session_state.get("transcript") or st.session_state.get("student_grade") or st.session_state.get("final_soap_text"):
            tab_labels.append("🧮 Grading")
            tab_renderers.append(self.grade_display.render)

        tabs = st.tabs(tab_labels)

        for tab, label, renderer in zip(tabs, tab_labels, tab_renderers):
            with tab:
                if label == "📄 SOAP Note":
                    st.markdown("### Professional SOAP Note")
                    st.markdown("*Ready for clinical documentation*")
                elif label == "📝 Transcript":
                    st.markdown("### Interview Transcript")
                    st.markdown("*Complete transcription of the audio*")
                elif label == "📋 Checklist":
                    st.markdown("### Checklist Evaluation")
                    st.markdown("*Generated from the uploaded or recorded interview*")
                elif label == "🧮 Grading":
                    st.markdown("### Final SOAP Note Grading")
                    st.markdown("*Upload the completed SOAP note, then run grading*")
                renderer()

        # Action buttons - clearer layout
        st.markdown("---")
        st.markdown("### What would you like to do next?")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🎙️ New Interview", type="primary", use_container_width=True):
                self._reset_workflow()

        with col2:
            if st.button("🔄 Reprocess Audio", use_container_width=True):
                # Clear prior outputs & flags then auto-run again on audio_input screen
                for k in ['soap_data','transcript','processing_started','processing_inflight','processing_complete','interview_content','transcription_result','soap_result','auto_checklist','student_grade','case_file','case_file_content','case_file_signature','case_title','final_soap_text','final_soap_signature','final_soap_name','final_soap_upload']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.workflow_stage = 'audio_input'
                st.rerun()

        with col3:
            if st.button("📁 Change Audio", use_container_width=True):
                # Clear current audio and derived outputs so the next recording starts clean.
                for k in [
                    'interview_file', 'processing_started', 'processing_inflight', 'processing_complete',
                    'downloading_recording', 'current_recording', 'soap_data', 'transcript',
                    'interview_content', 'transcription_result', 'soap_result',
                    'auto_checklist', 'student_grade', 'case_file', 'case_file_content',
                    'case_file_signature', 'case_title', 'final_soap_text',
                    'final_soap_signature', 'final_soap_name', 'final_soap_upload'
                ]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.workflow_stage = 'audio_input'
                st.rerun()
        
        
        
    def _on_file_upload_analysis(self):
        """Handle file upload analysis start: jump straight to processing and run pipeline."""
        # Ensure a clean processing state
        for k in ['processing_started', 'processing_inflight', 'processing_complete', 'soap_data', 'transcript', 'auto_checklist', 'student_grade', 'case_file', 'case_file_content', 'case_file_signature', 'case_title', 'final_soap_text', 'final_soap_signature', 'final_soap_name', 'final_soap_upload']:
            if k in st.session_state:
                del st.session_state[k]
        # Start processing immediately
        st.session_state.processing_started = True
        st.session_state.workflow_stage = 'processing'
        st.rerun()
    
    def _reset_workflow(self):
        """Reset the workflow to start"""
        # Debug: Show current session state before reset
        if st.session_state.get('debug_mode'):
            st.write("**Session state before reset:**", dict(st.session_state))
        
        # Clear ALL session state related to recording and processing
        keys_to_clear = [
            'interview_file', 'soap_note', 'soap_data', 'transcript',
            'downloading_recording', 'current_recording', 'room_name',
            'recording_timestamp', 'encounter_file', 'current_stage',
            'processing_complete', 'processing_started', 'processing_inflight', 'results_ready',
            'transcription_ready', 'soap_ready', 'selected_model',
            'selected_prompt', 'show_live_recorder', 'file_processed',
            'case_file', 'case_file_content', 'case_file_signature', 'case_title',
            'interview_content', 'transcription_result', 'soap_result',
            'auto_checklist', 'student_grade', 'final_soap_text',
            'final_soap_signature', 'final_soap_name', 'final_soap_upload'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Force reset to audio input stage
        st.session_state.workflow_stage = 'audio_input'
        
        # Debug: Show session state after reset
        if st.session_state.get('debug_mode'):
            st.write("**Session state after reset:**", dict(st.session_state))
        
        st.rerun()


class Navigation:
    def __init__(self):
        self.pages = {
            "🎯 CareScore AI": StreamlinedWorkflowPage(),
        }

    def render_header(self):
        """Header is now rendered by individual pages"""
        pass

    def render_sidebar(self):
        """Minimal, clean sidebar"""
        with st.sidebar:
            # Branding with compact gear icon for advanced settings
            top_cols = st.columns([4,1])
            with top_cols[0]:
                st.markdown("### CareScore AI")
                st.caption("AI Powered Clinical Documentation")
            with top_cols[1]:
                user = st.session_state.get('user', {})
                is_admin = user.get('role') == 'admin'
                if is_admin:
                    if 'show_advanced_settings' not in st.session_state:
                        st.session_state.show_advanced_settings = False
                    if st.button("⚙️", key="adv_settings_toggle", help="Toggle advanced developer settings (admin only)"):
                        st.session_state.show_advanced_settings = not st.session_state.show_advanced_settings
                        st.rerun()
                else:
                    # Non-admin: ensure advanced settings hidden
                    st.session_state.show_advanced_settings = False

            st.markdown("---")
            
            # Essential actions only
            if st.button("🔄 New", use_container_width=True):
                # Reset all session state for a fresh start
                keys_to_clear = [
                    'interview_file', 'soap_note', 'soap_data', 'transcript',
                    'downloading_recording', 'current_recording', 'room_name',
                    'recording_timestamp', 'encounter_file', 'current_stage',
                    'processing_complete', 'processing_started', 'processing_inflight', 'results_ready',
                    'transcription_ready', 'soap_ready', 'selected_model',
                    'selected_prompt', 'show_live_recorder', 'file_processed',
                    'case_file', 'case_file_content', 'case_file_signature', 'case_title',
                    'interview_content', 'transcription_result', 'soap_result',
                    'auto_checklist', 'student_grade', 'final_soap_text',
                    'final_soap_signature', 'final_soap_name', 'final_soap_upload'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.workflow_stage = 'audio_input'
                st.rerun()
            
            # Jump to results if available
            if st.session_state.get('soap_data') or st.session_state.get('transcript'):
                if st.button("📊 Results", use_container_width=True):
                    st.session_state.workflow_stage = 'results_ready'
                    st.rerun()
            
            # Compact advanced panel (appears immediately under section divider when toggled)
            if st.session_state.get('show_advanced_settings') and st.session_state.get('user', {}).get('role') == 'admin':
                with st.container(border=True):
                    st.caption("Advanced Settings")
                    # DEBUG MODE
                    if st.checkbox("🔍 Debug", key="debug_mode_toggle", help="Show internal session state & maintenance tools"):
                        debug_state = {k: v for k, v in st.session_state.items() if not k.startswith('_')}
                        st.json(debug_state)
                        if st.button("🔥 Force Reset", key="force_reset_btn", help="Clear ALL session state (except auth)", use_container_width=True):
                            keys_to_keep = ['authenticated', 'user']
                            for key in list(st.session_state.keys()):
                                if key not in keys_to_keep:
                                    del st.session_state[key]
                            st.session_state.workflow_stage = 'audio_input'
                            st.success("State cleared")
                            st.rerun()

                    # Model Configuration
                    if 'gemini_model' not in st.session_state:
                        st.session_state.gemini_model = 'gemini-3-pro-preview'

                    with st.expander("Model Configuration", expanded=False):
                        gemini_models = [
                            'gemini-3-pro-preview',
                            'gemini-3-flash-preview',
                            'gemini-2.5-pro',
                            'gemini-2.5-flash',
                            'gemini-2.0-flash',
                            'gemini-1.5-pro',
                            'gemini-1.5-flash'
                        ]
                        try:
                            g_index = gemini_models.index(st.session_state.gemini_model)
                        except ValueError:
                            g_index = 0
                        st.session_state.gemini_model = st.selectbox(
                            "Gemini Model",
                            gemini_models,
                            index=g_index,
                            help="Used for transcription + text generation (flash = speed, pro = quality)"
                        )
            
            # Logout
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
        
        # Always return the single page
        return "🎯 CareScore AI"
