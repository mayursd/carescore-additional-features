"""
File Uploader UI component
"""
import streamlit as st


class FileUploader:
    def render(self, on_analysis_start):
        """Improved file upload with better UX"""
        st.markdown("**Drag and drop your file or click to browse:**")
        
        uploaded_file = st.file_uploader(
            label="Choose audio/video file",
            type=["mp3", "mp4", "m4a", "wav", "mov", "avi", "flv", "webm"],
            help="Supported formats: MP3, MP4, M4A, WAV, MOV, AVI, FLV, WEBM (max 200MB)",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.success(f"✅ **{uploaded_file.name}** uploaded successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📁 **File Size:** {file_size_mb:.1f} MB")
            with col2:
                st.info(f"📄 **Type:** {uploaded_file.type}")
            
            st.session_state.encounter_file = uploaded_file
            st.session_state.interview_file = uploaded_file
            
            if st.button("🚀 Generate SOAP Note", type="primary", use_container_width=True):
                on_analysis_start()
        else:
            st.info("📝 **Tip:** Upload a clinical interview recording to generate a professional SOAP note")
            
            with st.expander("📋 Supported File Types & Tips"):
                st.markdown("""
                **Supported Audio Formats:**
                - MP3 (recommended for audio-only)
                - M4A (Apple format)
                - WAV (high quality, larger files)
                
                **Supported Video Formats:**
                - MP4 (recommended for video)
                - MOV (Apple video format)
                - AVI, FLV, WEBM (various video formats)
                
                **File Size Limit:** 200 MB maximum
                
                **Best Practices:**
                - Clear audio quality improves transcription accuracy
                - Minimize background noise
                - Ensure all speakers are audible
                - Interview length: 5-60 minutes works best
                """)
