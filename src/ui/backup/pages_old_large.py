import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Import modular components
from .pages_modular import show_streamlined_workflow


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


class Page:
    def render(self):
        pass


class Navigation:
    def __init__(self):
        self.pages = {
            "🎯 CareScore AI": StreamlinedWorkflowPage(),
        }

    def render_header(self):
        """Render clean header"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("src/ui/assets/logo.png", width=200)
        st.markdown("---")

    def render_sidebar(self):
        """Minimal sidebar for settings"""
        with st.sidebar:
            st.markdown("### ⚙️ Settings")
            
            # System Status section (read-only, secure)
            st.markdown("### 📊 System Status")
            
            # Check environment variables securely (backend only)
            gemini_status = "✅" if os.environ.get("GEMINI_AI_KEY") else "❌"
            daily_status = "✅" if os.environ.get("DAILY_API_KEY") else "❌"
            
            st.markdown(f"""
            **API Services:**
            - Gemini AI: {gemini_status}  
            - Daily.co: {daily_status}
            """)
            
            if not all([gemini_status == "✅", daily_status == "✅"]):
                st.warning("⚠️ Some API services are not configured. Contact your administrator.")
            else:
                st.success("✅ All services ready!")
            
        return "🎯 CareScore AI"

    def render(self):
        selected_page = self.render_sidebar()
        self.render_header()
        
        if selected_page in self.pages:
            self.pages[selected_page].render()
        else:
            st.error(f"Page '{selected_page}' not found.")


def main():
    st.set_page_config(
        page_title="CareScore AI",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    SessionState()
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: bold;
    }
    .main-container {
        padding: 1rem;
    }
    .logo-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize navigation
    nav = Navigation()
    nav.render()


if __name__ == "__main__":
    main()


class Page:
    def render(self):
        pass


class StreamlinedWorkflowPage(Page):
    def __init__(self):
        with open("src/config/carescore_ai_models.json", "r") as csaimodels:
            self.ai_model_cost_dict = json.load(csaimodels)
        self.soap_template = "src/templates/SOAP_Note_Template.docx"
        
        # Initialize workflow state
        if "workflow_stage" not in st.session_state:
            st.session_state.workflow_stage = "setup"
        if "auto_checklist" not in st.session_state:
            st.session_state.auto_checklist = None
        if "auto_soap" not in st.session_state:
            st.session_state.auto_soap = None
        if "interview_file" not in st.session_state:
            st.session_state.interview_file = None
        if "encounter_file" not in st.session_state:
            st.session_state.encounter_file = None
        if "interview_content" not in st.session_state:
            st.session_state.interview_content = None
        if "case_file_content" not in st.session_state:
            st.session_state.case_file_content = None
        if "room_name" not in st.session_state:
            st.session_state.room_name = ""
        if "recording_timestamp" not in st.session_state:
            st.session_state.recording_timestamp = None
        if "downloading_recording" not in st.session_state:
            st.session_state.downloading_recording = False
        if "current_recording" not in st.session_state:
            st.session_state.current_recording = None

    def render(self):
        # Progress indicator
        self.show_progress_indicator()
        
        # Step 1: Case Setup
        self.render_case_setup()
        
        # Step 2: Audio Recording/Upload
        self.render_audio_section()
        
        # Step 3: Automated Processing
        if st.session_state.workflow_stage in ["processing", "completed"]:
            self.render_automated_processing()
        
        # Step 4: Results
        if st.session_state.workflow_stage == "completed":
            self.render_results_section()

    def show_progress_indicator(self):
        """Clean progress indicator"""
        st.markdown("### 📋 Workflow Progress")
        
        steps = [
            ("📁", "Case Setup", ["audio_ready", "processing", "completed"]),
            ("🎙️", "Recording", ["processing", "completed"]),
            ("⚙️", "Analysis", ["completed"]),
            ("📊", "Results", ["completed"])
        ]
        
        cols = st.columns(4)
        for i, (icon, label, active_stages) in enumerate(steps):
            with cols[i]:
                is_active = st.session_state.workflow_stage in active_stages
                is_current = (
                    (i == 0 and st.session_state.workflow_stage == "setup") or
                    (i == 1 and st.session_state.workflow_stage == "audio_ready") or
                    (i == 2 and st.session_state.workflow_stage == "processing") or
                    (i == 3 and st.session_state.workflow_stage == "completed")
                )
                
                if is_active:
                    color = "green"
                    status_icon = "✅"
                elif is_current:
                    color = "orange"
                    status_icon = "🔄"
                else:
                    color = "gray"
                    status_icon = "⏳"
                
                st.markdown(
                    f'<div style="text-align: center; color: {color}; padding: 10px; border-radius: 5px; background-color: {"#f0f8f0" if is_active else "#f8f8f8" if is_current else "#f5f5f5"};">'
                    f'<h3>{status_icon}</h3>'
                    f'<p><strong>{icon} {label}</strong></p>'
                    f'</div>', 
                    unsafe_allow_html=True
                )
        
        st.markdown("---")

    def render_case_setup(self):
        """Simplified case setup"""
        st.markdown("### 📁 Case Setup")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.case_file = st.file_uploader(
                    "📋 Patient Case File", 
                    type=["txt", "docx", "pdf"],
                    help="Upload the patient case file for evaluation"
                )
                
            with col2:
                st.session_state.care_objectives_file = st.file_uploader(
                    "🎯 Care Objectives", 
                    type=["csv", "pdf"],
                    help="Upload the care objectives/grading criteria"
                )
            
            # Case title
            st.session_state.case_title = st.text_input(
                "📝 Case Title",
                placeholder="e.g., Patient Interview - Emergency Room",
                help="Enter a descriptive title for this evaluation session"
            )
            
            # Debug case setup
            with st.expander("Case Setup Debug"):
                st.write(f"Case file: {bool(st.session_state.get('case_file'))}")
                st.write(f"Care objectives: {bool(st.session_state.get('care_objectives_file'))}")
                st.write(f"Case title: {st.session_state.get('case_title', '')}")
                st.write(f"Current workflow stage: {st.session_state.workflow_stage}")
            
            # Setup completion check
            if (st.session_state.case_file and 
                st.session_state.care_objectives_file and 
                st.session_state.case_title and 
                st.session_state.workflow_stage == "setup"):
                
                # Process case file content
                with st.spinner("Processing case files..."):
                    try:
                        st.session_state.case_file_content = get_file_content(st.session_state.case_file)
                        st.success("✅ Case setup completed!")
                        st.session_state.workflow_stage = "audio_ready"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error processing case file: {e}")
                        st.session_state.case_file_content = ""
            
            # Alternative: Skip case setup for testing
            if st.session_state.workflow_stage == "setup":
                st.markdown("---")
                if st.button("⚡ Skip Case Setup (For Testing)", type="secondary"):
                    st.session_state.case_file_content = "Test case content"
                    st.session_state.case_title = "Test Case"
                    st.session_state.workflow_stage = "audio_ready"
                    st.rerun()

    def render_audio_section(self):
        """Simplified audio recording section"""
        if st.session_state.workflow_stage in ["setup"]:
            st.markdown("### 🎙️ Audio Recording")
            st.info("👆 Complete the case setup above to proceed.")
            return
            
        st.markdown("### 🎙️ Audio Recording")
        
        # Debug info
        with st.expander("Debug Info"):
            st.write(f"Workflow Stage: {st.session_state.workflow_stage}")
            st.write(f"Interview File: {st.session_state.get('interview_file', 'None')}")
            st.write(f"Has Interview File: {bool(st.session_state.get('interview_file'))}")
        
        # Show status based on workflow stage
        if st.session_state.workflow_stage in ["processing", "completed"]:
            if st.session_state.get('interview_file'):
                st.success("✅ Audio recording completed!")
            else:
                st.warning("⚠️ No audio file found.")
        elif st.session_state.workflow_stage == "audio_ready":
            if st.session_state.get('interview_file'):
                st.success("✅ Audio ready for analysis!")
                if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                    self.start_automated_processing()
            else:
                self.render_recording_options()
        else:
            self.render_recording_options()

    def render_recording_options(self):
        """Simplified recording options"""
        with st.container(border=True):
            tab1, tab2, tab3 = st.tabs(["🎙️ Live Recording", "📁 Upload File", "🔍 Retrieve Recording"])
            
            with tab1:
                self.render_live_recorder()
                
            with tab2:
                self.render_file_upload()
                
            with tab3:
                self.render_recording_retrieval()

    def render_live_recorder(self):
        """Simplified live recorder"""
        col1, col2 = st.columns([3, 1])
        with col1:
            room_name = st.text_input(
                "Room Name", 
                value=st.session_state.get('room_name', ''),
                placeholder="Enter room name (e.g., sim-room-1)"
            )
        with col2:
            if st.button("🎲 Random"):
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                st.session_state.room_name = f"room-{random_name}"
                st.rerun()
        
        if room_name:
            st.session_state.room_name = room_name
        
        if not st.session_state.get('room_name'):
            st.warning("⚠️ Please enter a room name to start recording.")
            return
            
        # Generate timestamp if needed
        if "recording_timestamp" not in st.session_state:
            st.session_state.recording_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Check Daily API key
        daily_api_key = os.environ.get("DAILY_API_KEY", "")
        if not daily_api_key:
            st.error("⚠️ Daily API Key not configured.")
            return
            
        # Embed recorder
        iframe_url = f"http://127.0.0.1:5500/src/static/main.html?apikey={daily_api_key}&roomName={st.session_state.room_name}&timestamp={st.session_state.recording_timestamp}"
        
        components.html(
            f"""<iframe src='{iframe_url}' 
                width='100%' 
                height='500px'
                allow='microphone; camera; autoplay; display-capture'
                sandbox='allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation'></iframe>""",
            height=500,
        )
        
        if st.button("🎵 Process Recording", type="primary", use_container_width=True):
            self.process_recorded_audio()

    def render_file_upload(self):
        """Simplified file upload"""
        uploaded_file = st.file_uploader(
            "Choose audio/video file",
            type=["mp3", "mp4", "m4a", "wav", "mov"],
            help="Upload a pre-recorded interview"
        )
        
        if uploaded_file:
            st.session_state.encounter_file = uploaded_file
            st.session_state.interview_file = uploaded_file
            st.success(f"✅ File '{uploaded_file.name}' uploaded!")
            
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                self.start_automated_processing()

    def render_recording_retrieval(self):
        """Retrieve recordings from Daily.co"""
        st.markdown("Search and retrieve recordings from Daily.co")
        
        # Check Daily API key
        daily_api_key = os.environ.get("DAILY_API_KEY", "")
        if not daily_api_key:
            st.error("⚠️ Daily API Key not configured.")
            return
        
        # Debug session state
        st.write("**🔍 Debug Session State:**")
        st.write(f"- downloading_recording: {st.session_state.get('downloading_recording', False)}")
        st.write(f"- current_recording exists: {bool(st.session_state.get('current_recording'))}")
        st.write(f"- workflow_stage: {st.session_state.get('workflow_stage', 'none')}")
        
        # CRITICAL: Check for download state FIRST, before rendering any buttons
        if st.session_state.get('downloading_recording'):
            st.info("⬇️ Download in progress... Please wait.")
            self.handle_download_process()
            return  # Important: return here to prevent rendering buttons
        
        # Only show search interface if NOT downloading
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input(
                "Search recordings by room name",
                placeholder="Enter room name or part of it"
            )
        with col2:
            if st.button("🔍 Search"):
                if search_query:
                    self.search_and_display_recordings(search_query)
                else:
                    st.warning("Please enter a search term")
        
        # List all recordings button
        if st.button("📋 List All Recordings", use_container_width=True):
            self.list_all_recordings()

    def search_and_display_recordings(self, search_query):
        """Search for recordings matching the query"""
        with st.spinner("🔍 Searching recordings..."):
            try:
                all_recordings = list_recordings()
                matching_recordings = [
                    rec for rec in all_recordings 
                    if search_query.lower() in rec.get('room_name', '').lower()
                ]
                
                if not matching_recordings:
                    st.warning(f"No recordings found matching '{search_query}'")
                    return
                
                st.success(f"Found {len(matching_recordings)} recording(s)")
                
                for i, recording in enumerate(matching_recordings):
                    with st.expander(f"Recording {i+1}: {recording.get('room_name', 'Unknown')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Room:** {recording.get('room_name', 'Unknown')}")
                            st.write(f"**Duration:** {recording.get('duration', 'Unknown')} seconds")
                            st.write(f"**Created:** {recording.get('start_time', 'Unknown')}")
                            
                        with col2:
                            # Create a unique key for this recording
                            button_key = f"use_rec_{i}"
                            if st.button(f"📥 Use Recording {i+1}", key=button_key):
                                # Debug: Show what's happening
                                st.write(f"🔥 **BUTTON CLICKED for recording {i+1}**")
                                st.write(f"- Recording ID: {recording.get('id')}")
                                st.write(f"- Before - downloading_recording: {st.session_state.get('downloading_recording', False)}")
                                
                                # Store the recording data directly
                                st.session_state.downloading_recording = True
                                st.session_state.current_recording = recording
                                
                                st.write(f"- After - downloading_recording: {st.session_state.get('downloading_recording', False)}")
                                st.write(f"- Current recording stored: {bool(st.session_state.get('current_recording'))}")
                                
                                # Force immediate rerun
                                st.rerun()
                                
            except Exception as e:
                st.error(f"Error searching recordings: {str(e)}")

    def list_all_recordings(self):
        """List all available recordings"""
        with st.spinner("📋 Loading all recordings..."):
            try:
                all_recordings = list_recordings()
                
                if not all_recordings:
                    st.warning("No recordings found")
                    return
                
                st.success(f"Found {len(all_recordings)} recording(s)")
                
                for i, recording in enumerate(all_recordings):
                    with st.expander(f"Recording {i+1}: {recording.get('room_name', 'Unknown')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Room:** {recording.get('room_name', 'Unknown')}")
                            st.write(f"**Duration:** {recording.get('duration', 'Unknown')} seconds")
                            st.write(f"**Created:** {recording.get('start_time', 'Unknown')}")
                            
                        with col2:
                            # Create a unique key for this recording
                            button_key = f"use_all_rec_{i}"
                            if st.button(f"📥 Use Recording {i+1}", key=button_key):
                                # Debug: Show what's happening
                                st.write(f"🔥 **BUTTON CLICKED for recording {i+1}**")
                                st.write(f"- Recording ID: {recording.get('id')}")
                                st.write(f"- Before - downloading_recording: {st.session_state.get('downloading_recording', False)}")
                                
                                # Store the recording data directly
                                st.session_state.downloading_recording = True
                                st.session_state.current_recording = recording
                                
                                st.write(f"- After - downloading_recording: {st.session_state.get('downloading_recording', False)}")
                                st.write(f"- Current recording stored: {bool(st.session_state.get('current_recording'))}")
                                
                                # Force immediate rerun
                                st.rerun()
                                
            except Exception as e:
                st.error(f"Error listing recordings: {str(e)}")

    def handle_download_process(self):
        """Handle the download process with visible progress"""
        if not st.session_state.get('current_recording'):
            st.error("❌ No recording selected")
            st.session_state.downloading_recording = False
            return
            
        recording = st.session_state.current_recording
        
        try:
            # Show progress
            progress_container = st.container()
            with progress_container:
                st.write(f"🔍 **Processing Recording:**")
                st.write(f"- Recording ID: {recording.get('id')}")
                st.write(f"- Room Name: {recording.get('room_name')}")
                st.write(f"- Current workflow stage: {st.session_state.workflow_stage}")
                
                recording_id = recording.get('id')
                if not recording_id:
                    st.error("❌ No recording ID found")
                    st.session_state.downloading_recording = False
                    return
                
                # Step 1: Get download link
                with st.spinner("🔗 Getting download link..."):
                    download_url = get_recording_download_link(recording_id)
                
                if not download_url:
                    st.error("❌ Failed to get download link")
                    st.session_state.downloading_recording = False
                    return
                    
                st.success(f"✅ Got download URL")
                
                # Step 2: Download video
                with st.spinner("⬇️ Downloading video file..."):
                    video_path = download_video(download_url)
                
                if not video_path or not os.path.exists(video_path):
                    st.error("❌ Failed to download recording file")
                    st.session_state.downloading_recording = False
                    return
                    
                st.success(f"✅ Downloaded successfully")
                
                # Step 3: Process file
                with st.spinner("📁 Processing downloaded file..."):
                    # Read the file and create BytesIO object
                    with open(video_path, 'rb') as f:
                        video_content = f.read()
                        video_bytes = io.BytesIO(video_content)
                        video_bytes.name = f"{recording.get('room_name', 'recording')}.mp4"
                        video_bytes.type = "video/mp4"
                        
                    # Set session state
                    st.session_state.interview_file = video_bytes
                    st.session_state.workflow_stage = "audio_ready"
                    
                    # Clean up temporary file
                    if os.path.exists(video_path):
                        os.unlink(video_path)
                
                st.success("✅ Recording ready for analysis!")
                st.balloons()  # Celebration animation
                
                # Show what was set
                st.write(f"🎯 **Session State Updated:**")
                st.write(f"- Interview file size: {len(video_content):,} bytes")
                st.write(f"- Workflow stage: {st.session_state.workflow_stage}")
                
                # Clear download state
                st.session_state.downloading_recording = False
                st.session_state.current_recording = None
                
                st.info("🔄 Refreshing to show analysis options...")
                time.sleep(2)
                st.rerun()
                        
        except Exception as e:
            st.error(f"❌ Error downloading recording: {str(e)}")
            st.write(f"**Exception Type:** {type(e).__name__}")
            st.code(f"Full traceback:\n{traceback.format_exc()}")
            st.session_state.downloading_recording = False
            st.session_state.current_recording = None

    def process_recorded_audio(self):
        """Process Daily.co recording"""
        if not st.session_state.get('room_name'):
            st.error("❌ No room name found.")
            return
            
        with st.spinner("🔍 Searching for recording..."):
            try:
                all_recordings = list_recordings()
                matching_recordings = [
                    rec for rec in all_recordings 
                    if st.session_state.room_name.lower() in rec.get('room_name', '').lower()
                ]
                
                if not matching_recordings:
                    st.error(f"❌ No recordings found for room '{st.session_state.room_name}'.")
                    return
                
                recording = matching_recordings[0]
                st.success(f"✅ Found recording: {recording.get('room_name', 'Unknown')}")
                
                # Download recording
                with st.spinner("⬇️ Downloading recording..."):
                    recording_id = recording.get('id')
                    download_url = get_recording_download_link(recording_id)
                    video_path = download_video(download_url)
                    
                    if video_path and os.path.exists(video_path):
                        with open(video_path, 'rb') as f:
                            video_bytes = io.BytesIO(f.read())
                            video_bytes.name = f"{st.session_state.room_name}_{st.session_state.recording_timestamp}.mp4"
                            video_bytes.type = "audio/mp4"
                            
                        st.session_state.interview_file = video_bytes
                        st.session_state.workflow_stage = "audio_ready"
                        
                        st.success("🎉 Recording processed successfully!")
                        
                        # Clean up
                        if os.path.exists(video_path):
                            os.unlink(video_path)
                    else:
                        st.error("❌ Failed to download recording.")
                        
            except Exception as e:
                st.error(f"❌ Error processing recording: {str(e)}")

    def start_automated_processing(self):
        """Start automated processing"""
        st.session_state.workflow_stage = "processing"
        st.rerun()

    # def render_automated_processing(self):

    # def run_automated_pipeline(self):

    def download_and_use_recording(self, recording):

        print("in here")
        """Download and use a selected recording"""
        try:
            # Debug info first
            st.write(f"🔍 **DEBUG INFO:**")
            st.write(f"- Recording ID: {recording.get('id')}")
            st.write(f"- Room Name: {recording.get('room_name')}")
            st.write(f"- Current workflow stage: {st.session_state.workflow_stage}")

            recording_id = recording.get('id')
            if not recording_id:
                st.error("❌ No recording ID found")
                return
                
            # Step 1: Get download link
            st.info("🔗 Getting download link...")
            download_url = get_recording_download_link(recording_id)
            
            if not download_url:
                st.error("❌ Failed to get download link")
                return
                
            st.success(f"✅ Got download URL: {download_url[:50]}...")
            
            # Step 2: Download video
            st.info("⬇️ Downloading video file...")
            video_path = download_video(download_url)
            
            if not video_path or not os.path.exists(video_path):
                st.error("❌ Failed to download recording file")
                return
                
            st.success(f"✅ Downloaded to: {video_path}")
            
            # Step 3: Process file
            st.info("📁 Processing downloaded file...")
            
            # Read the file and create BytesIO object
            with open(video_path, 'rb') as f:
                video_content = f.read()
                video_bytes = io.BytesIO(video_content)
                video_bytes.name = f"{recording.get('room_name', 'recording')}.mp4"
                video_bytes.type = "video/mp4"
                
            # Step 4: Set session state
            st.session_state.interview_file = video_bytes
            st.session_state.workflow_stage = "audio_ready"
            
            # Clean up temporary file
            if os.path.exists(video_path):
                os.unlink(video_path)
                
            st.success("✅ Recording ready for analysis!")
            st.balloons()  # Celebration animation
            
            # Show what was set
            st.write(f"� **Session State Updated:**")
            st.write(f"- Interview file size: {len(video_content)} bytes")
            st.write(f"- Workflow stage: {st.session_state.workflow_stage}")
            
            st.info("🔄 Page will refresh in 2 seconds to show the analysis button...")
            
            # Force rerun to update the UI
            time.sleep(2)
            st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Error downloading recording: {str(e)}")
            st.write(f"**Exception Type:** {type(e).__name__}")
            st.code(f"Full traceback:\n{traceback.format_exc()}")

    def process_recorded_audio(self):
        """Process Daily.co recording"""
        if not st.session_state.get('room_name'):
            st.error("❌ No room name found.")
            return
            
        with st.spinner("🔍 Searching for recording..."):
            try:
                all_recordings = list_recordings()
                matching_recordings = [
                    rec for rec in all_recordings 
                    if st.session_state.room_name.lower() in rec.get('room_name', '').lower()
                ]
                
                if not matching_recordings:
                    st.error(f"❌ No recordings found for room '{st.session_state.room_name}'.")
                    return
                
                recording = matching_recordings[0]
                st.success(f"✅ Found recording: {recording.get('room_name', 'Unknown')}")
                
                # Download recording
                with st.spinner("⬇️ Downloading recording..."):
                    recording_id = recording.get('id')
                    download_url = get_recording_download_link(recording_id)
                    video_path = download_video(download_url)
                    
                    if video_path and os.path.exists(video_path):
                        with open(video_path, 'rb') as f:
                            video_bytes = io.BytesIO(f.read())
                            video_bytes.name = f"{st.session_state.room_name}_{st.session_state.recording_timestamp}.mp4"
                            video_bytes.type = "audio/mp4"
                            
                        st.session_state.interview_file = video_bytes
                        st.session_state.workflow_stage = "audio_ready"
                        
                        st.success("🎉 Recording processed successfully!")
                        
                        # Clean up
                        if os.path.exists(video_path):
                            os.unlink(video_path)
                    else:
                        st.error("❌ Failed to download recording.")
                        
            except Exception as e:
                st.error(f"❌ Error processing recording: {str(e)}")

    def start_automated_processing(self):
        """Start automated processing"""
        st.session_state.workflow_stage = "processing"
        st.rerun()


    def render_automated_processing(self):
        """Simplified automated processing"""
        st.markdown("### ⚙️ Automated Analysis")
        
        if st.session_state.workflow_stage == "processing":
            with st.spinner("🔄 Processing your interview..."):
                self.run_automated_pipeline()
        else:
            st.success("✅ Analysis completed!")
            
        if st.button("🔄 Re-run Analysis"):
            st.session_state.auto_checklist = None
            st.session_state.auto_soap = None
            st.session_state.workflow_stage = "processing"
            st.rerun()

    def run_automated_pipeline(self):
        """Run automated pipeline without debug output"""
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Transcribe audio
            status_text.text("🎯 Step 1/4: Transcribing audio...")
            progress_bar.progress(25)
            
            if not st.session_state.interview_content:
                if st.session_state.interview_file:
                    st.session_state.interview_content = get_file_content(st.session_state.interview_file)
                else:
                    st.error("❌ No audio recording found.")
                    st.session_state.workflow_stage = "audio_ready"
                    return
            
            # Step 2: Generate checklist
            status_text.text("📋 Step 2/4: Generating checklist...")
            progress_bar.progress(50)
            
            if not st.session_state.auto_checklist:
                st.session_state.auto_checklist = self.generate_automated_checklist()
            
            # Step 3: Generate SOAP note
            status_text.text("📄 Step 3/4: Generating SOAP note...")
            progress_bar.progress(75)
            
            if not st.session_state.auto_soap:
                st.session_state.auto_soap = self.generate_automated_soap()
            
            # Step 4: Complete
            status_text.text("✅ Step 4/4: Analysis complete!")
            progress_bar.progress(100)
            
            st.session_state.workflow_stage = "completed"
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Processing failed: {str(e)}")
            st.session_state.workflow_stage = "audio_ready"

    def generate_automated_checklist(self):
        """Generate checklist"""
        try:
            case_content = get_file_content(st.session_state.case_file)
            if not case_content:
                return None
            
            # Count checklist items
            count_response = llm_call(
                model=st.session_state.get('gemini_model', 'gemini-2.5-pro'),
                messages=self.checklist_count_message(case_content),
            )
            
            # Extract checklist
            checklist_response = llm_call(
                model=st.session_state.get('gemini_model', 'gemini-2.5-pro'),
                messages=self.checklist_extraction_message(case_content),
                format="json",
            )
            
            checklist_content = checklist_response["choices"][0]["message"]["content"]
            checklist_data = json.loads(checklist_content)
            
            # Evaluate if interview available
            if st.session_state.interview_content:
                evaluation_response = llm_call(
                    model=st.session_state.get('gemini_model', 'gemini-2.5-pro'),
                    messages=self.checklist_evaluation_message(checklist_data["questions_and_answers"]),
                    format="json",
                )
                
                evaluation_content = evaluation_response["choices"][0]["message"]["content"]
                evaluated_checklist = json.loads(evaluation_content)
                return evaluated_checklist.get("CheckList Evaluation", checklist_data.get("questions_and_answers", []))
            
            return checklist_data.get("questions_and_answers", [])
            
        except Exception as e:
            st.error(f"Failed to generate checklist: {str(e)}")
            return None

    def generate_automated_soap(self):
        """Generate SOAP note"""
        try:
            if not st.session_state.interview_content:
                return None
            
            # Handle both string and dictionary formats
            if isinstance(st.session_state.interview_content, dict):
                interview_text = st.session_state.interview_content["interview"]
            else:
                interview_text = str(st.session_state.interview_content)
                
            # Check if Gemini API key is configured (backend only)
            if not os.environ.get('GEMINI_AI_KEY'):
                st.error("❌ Gemini API key not configured. Contact your administrator.")
                return None
            
            if not os.path.exists(self.soap_template):
                st.error(f"❌ SOAP template not found.")
                return None
            
            # Extract SOAP data for display
            soap_response = extract_soap_data(interview_text)
            
            if soap_response and "soap_data" in soap_response:
                st.session_state.soap_data = soap_response["soap_data"]
                return "SOAP_DATA_EXTRACTED"
            else:
                st.error("Failed to extract SOAP data.")
                return None
            
        except Exception as e:
            st.error(f"Failed to generate SOAP note: {str(e)}")
            return None

    def render_results_section(self):
        """Display results"""
        st.markdown("### 📊 Generated Reports")
        
        tab1, tab2, tab3 = st.tabs(["📋 Checklist", "📄 SOAP Note", "📝 Transcript"])
        
        with tab1:
            self.display_checklist_results()
            
        with tab2:
            self.display_soap_results()
            
        with tab3:
            self.display_interview_results()

    def display_checklist_results(self):
        """Display checklist results"""
        if st.session_state.auto_checklist:
            st.markdown("#### 📋 Checklist Evaluation")
            
            if isinstance(st.session_state.auto_checklist, list):
                checklist_data = st.session_state.auto_checklist
            else:
                checklist_data = st.session_state.auto_checklist.get("questions_and_answers", [])
            
            if checklist_data:
                df = pd.DataFrame(checklist_data)
                st.dataframe(df, use_container_width=True)
                
                # Download PDF
                if st.button("📥 Download Checklist PDF", type="secondary"):
                    try:
                        yes_count = sum(1 for item in checklist_data if item.get("Evaluated", "").lower() == "yes")
                        no_count = len(checklist_data) - yes_count
                        
                        generate_checklist_pdf(
                            checklist_data, 
                            yes_count, 
                            no_count, 
                            f"{st.session_state.case_title}_checklist.pdf"
                        )
                        
                        with open(f"{st.session_state.case_title}_checklist.pdf", "rb") as f:
                            st.download_button(
                                "📄 Download PDF",
                                f,
                                f"{st.session_state.case_title}_checklist.pdf",
                                mime="application/pdf"
                            )
                    except Exception as e:
                        st.error(f"Failed to generate PDF: {str(e)}")
        else:
            st.warning("Checklist not generated yet.")

    def display_soap_results(self):
        """Display SOAP note results"""
        if hasattr(st.session_state, 'soap_data') and st.session_state.soap_data:
            st.markdown("#### 📄 SOAP Note")
            soap_data = st.session_state.soap_data
            
            # Subjective Section
            st.markdown("##### 📝 Subjective")
            with st.expander("History of Present Illness (HPI)", expanded=True):
                st.text_area("HPI", soap_data.get("HPI", "Not documented"), height=100, disabled=True)
            
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("Past Medical History"):
                    st.text_area("PMHx", soap_data.get("PMHx", "Not documented"), height=80, disabled=True)
                with st.expander("Medications"):
                    st.text_area("Medications", soap_data.get("Medications", "Not documented"), height=80, disabled=True)
                    
            with col2:
                with st.expander("Family History"):
                    st.text_area("FHx", soap_data.get("FHx", "Not documented"), height=80, disabled=True)
                with st.expander("Allergies"):
                    st.text_area("Allergies", soap_data.get("Allergies", "Not documented"), height=80, disabled=True)
            
            # Social History
            with st.expander("Social History"):
                if isinstance(soap_data.get("SHx"), dict):
                    shx_text = "\n".join([f"{k}: {v}" for k, v in soap_data["SHx"].items() if v])
                else:
                    shx_text = str(soap_data.get("SHx", "Not documented"))
                st.text_area("Social History", shx_text, height=100, disabled=True)
            
            # Review of Systems
            with st.expander("Review of Systems"):
                if isinstance(soap_data.get("Review_of_Systems"), dict):
                    ros_text = "\n".join([f"{k}: {v}" for k, v in soap_data["Review_of_Systems"].items() if v])
                else:
                    ros_text = str(soap_data.get("Review_of_Systems", "Not documented"))
                st.text_area("Review of Systems", ros_text, height=150, disabled=True)
            
            # Objective Section
            st.markdown("##### 🔍 Objective")
            with st.expander("Physical Exam", expanded=True):
                if isinstance(soap_data.get("Objective"), dict):
                    obj_text = "\n".join([f"{k}: {v}" for k, v in soap_data["Objective"].items() if v])
                else:
                    obj_text = str(soap_data.get("Objective", "Not documented"))
                st.text_area("Physical Exam", obj_text, height=150, disabled=True)
            
            # Assessment & Plan Section
            st.markdown("##### 🎯 Assessment & Plan")
            with st.expander("Assessment & Plan", expanded=True):
                if isinstance(soap_data.get("Assessment_Plan"), dict):
                    ap_text = "\n".join([f"{k}: {v}" for k, v in soap_data["Assessment_Plan"].items() if v])
                else:
                    ap_text = str(soap_data.get("Assessment_Plan", "Not documented"))
                st.text_area("Assessment & Plan", ap_text, height=150, disabled=True)
            
            # Download Word document
            st.markdown("---")
            if st.button("📥 Generate & Download SOAP Note (Word Document)", use_container_width=True):
                with st.spinner("Creating Word document..."):
                    if isinstance(st.session_state.interview_content, dict):
                        interview_text = st.session_state.interview_content["interview"]
                    else:
                        interview_text = str(st.session_state.interview_content)
                    
                    soap_bytes = populate_soap_template(
                        self.soap_template,
                        interview_text,
                        ai_suggestions_enabled=True,
                        use_ai_assessment_plan=True
                    )
                    
                    if soap_bytes:
                        st.download_button(
                            "📄 Download Word Document",
                            soap_bytes,
                            f"{st.session_state.case_title}_SOAP.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                        st.success("✅ Word document ready!")
                    else:
                        st.error("❌ Failed to create Word document")
        else:
            st.warning("SOAP note not generated yet.")

    def display_interview_results(self):
        """Display interview transcript"""
        if st.session_state.get('interview_content'):
            st.markdown("#### 📝 Interview Transcript")
            
            if isinstance(st.session_state.interview_content, dict):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_area(
                        "Full Interview", 
                        st.session_state.interview_content.get("interview", "No content"), 
                        height=400
                    )
                    
                with col2:
                    st.text_area(
                        "Summary", 
                        st.session_state.interview_content.get("summary", "No summary"), 
                        height=400
                    )
            else:
                st.text_area("Interview Content", str(st.session_state.interview_content), height=400)
        else:
            st.warning("Interview transcript not available.")

    # Helper methods for checklist generation
    def checklist_count_message(self, case_file_content):
        consolidated_prompt = f"""You are a clinician in Medical hospital. You count checklist items from the case file.

        {CHECKLIST_COUNT_PROMPT}

        Grading File:
        {case_file_content}"""
        
        return [{"role": "user", "content": consolidated_prompt}]

    def checklist_extraction_message(self, case_file_content, expected_count=None):
        prompt = CHECKLIST_RETRIEVAL_PROMPT
        if expected_count:
            prompt = prompt.format(expected_count=expected_count)
        
        consolidated_prompt = f"""You are a clinician in Medical hospital. You extract the complete checklist from the case file.

        {prompt}

        Grading File:
        {case_file_content}

        CHECKLIST_SAMPLE_JSON:
        {CHECKLIST_SAMPLE_JSON}"""
        
        return [{"role": "user", "content": consolidated_prompt}]

    def checklist_evaluation_message(self, checklist_questions):
        consolidated_prompt = f"""You are a clinician in Medical hospital. You extract the complete checklist from the case file.

{CHECKLIST_EVALUATION_PROMPT}

CheckList Evaluation:
{str(checklist_questions)}

Clinician-Patient Interview:
{st.session_state.interview_content["interview"]}"""
        
        return [{"role": "user", "content": consolidated_prompt}]


class Navigation:
    def __init__(self):
        self.pages = {
            "🎯 CareScore AI": StreamlinedWorkflowPage(),
        }

    def render_header(self):
        """Render clean header"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("src/ui/assets/logo.png", width=200)
        st.markdown("---")

    def render_sidebar(self):
        """Minimal sidebar for settings"""
        with st.sidebar:
            st.markdown("### ⚙️ Settings")
            
            # System Status section (read-only, secure)
            st.markdown("### 📊 System Status")
            
            # Check environment variables securely (backend only)
            gemini_status = "✅" if os.environ.get("GEMINI_AI_KEY") else "❌"
            daily_status = "✅" if os.environ.get("DAILY_API_KEY") else "❌"
            
            st.markdown(f"""
            **API Services:**
            - Gemini AI: {gemini_status}  
            - Daily.co: {daily_status}
            """)
            
            if not all([gemini_status == "✅", daily_status == "✅"]):
                st.warning("⚠️ Some API services are not configured. Contact your administrator.")
            else:
                st.success("✅ All services ready!")
            
        return "🎯 CareScore AI"
