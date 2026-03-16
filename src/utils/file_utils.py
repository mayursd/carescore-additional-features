import streamlit as st
try:
    import fitz  # PyMuPDF
    _PDF_ENABLED = True
except ImportError:
    fitz = None
    _PDF_ENABLED = False
import pandas as pd
from docx import Document
import tempfile
import os
from src.utils.audio_video_utils import AudioVideoToNoteGenerator

def get_file_content(uploaded_file):
    try:
        if uploaded_file is not None:
            # Handle different types of file inputs
            if isinstance(uploaded_file, str):
                # If it's a file path string, we need to handle it differently
                # For now, return an error message
                st.error("Cannot process file path strings directly. Please use a file object.")
                return None
            
            # Check if it's a BytesIO object with custom attributes (Daily.co recording)
            if hasattr(uploaded_file, 'getvalue') and hasattr(uploaded_file, 'type') and hasattr(uploaded_file, 'name'):
                # Handle BytesIO objects from Daily.co recordings
                if uploaded_file.type in [
                    'audio/x-m4a', 'audio/x-mp3', 'audio/mpeg', 'audio/mp3',
                    'video/mp4', 'audio/mp4', 'video/quicktime', 'audio/wav',
                    'audio/x-wav', 'video/x-msvideo'
                ]:  
                    try:
                        # Create temporary file for Gemini processing
                        print(uploaded_file.type)
                        file_extension = os.path.splitext(uploaded_file.name)[1] or '.tmp'
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name
                        
                        # Pass the file path, and preserve the original MIME type
                        ang = AudioVideoToNoteGenerator()
                        file_content = ang.generate_note(uploaded_file=temp_file_path, mime_type=uploaded_file.type)
                        
                        # Clean up temporary file
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                        
                        return file_content
                    except Exception as e:
                        # Clean up temp file on error
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                        st.error(f"Error processing audio/video file: {str(e)}")
                        return None
            
            # Handle regular Streamlit uploaded files
            if not hasattr(uploaded_file, 'type'):
                st.error("Uploaded file object does not have a type attribute.")
                return None
                
            file_content = ""
            if uploaded_file.type == "text/plain":
                file_content = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "text/markdown":
                file_content = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                try:
                    doc = Document(uploaded_file)
                    file_content = "\n".join([para.text for para in doc.paragraphs])
                except Exception as e:
                    st.error(f"Error processing Word document: {str(e)}")
                    return None
            elif uploaded_file.type == "application/pdf":
                if not _PDF_ENABLED:
                    st.error("PDF processing not available: PyMuPDF (fitz) not installed. Please install dependencies.")
                    return None
                try:
                    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    file_content = ""
                    for page_num in range(pdf_document.page_count):
                        page = pdf_document.load_page(page_num)
                        file_content += page.get_text("text")
                except Exception as e:
                    st.error(f"Error processing PDF document: {str(e)}")
                    return None
            elif uploaded_file.type == "text/csv":
                try:
                    file_content = pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Error processing CSV file: {str(e)}")
                    return None
            elif uploaded_file.type in [
                'audio/x-m4a', 'audio/x-mp3', 'audio/mpeg', 'audio/mp3',
                'video/mp4', 'audio/mp4', 'video/quicktime', 'audio/wav',
                'audio/x-wav', 'video/x-msvideo'
            ]:
                try:
                    if hasattr(uploaded_file, 'getvalue'):  # BytesIO (Daily video)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name
                        # Pass the file path, and preserve the original MIME type
                        ang = AudioVideoToNoteGenerator()
                        file_content = ang.generate_note(uploaded_file=temp_file_path, mime_type=uploaded_file.type)
                        os.unlink(temp_file_path)
                    else:  # Regular uploaded file
                        ang = AudioVideoToNoteGenerator()
                        file_content = ang.generate_note(uploaded_file=uploaded_file, mime_type=uploaded_file.type)
                except Exception as e:
                    st.error(f"Error processing audio/video file: {str(e)}")
                    return None
            return file_content
        return None
    except Exception as e:
        st.error(f"Unexpected error processing file: {str(e)}")
        return None