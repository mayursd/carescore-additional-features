"""
Case Setup Component
Handles patient case file and care objectives upload
"""
import streamlit as st
from src.utils.file_utils import get_file_content


class CaseSetup:
    def render(self):
        """Optional case setup used for checklist and grading features."""
        with st.container(border=True):
            st.markdown("### 📁 Optional Evaluation Context")
            st.caption("Upload a case file if you want checklist extraction and SOAP grading.")

            uploaded_case = st.file_uploader(
                "📋 Patient Case File", 
                type=["txt", "docx", "pdf"],
                help="Upload the patient case file used to extract checklist items and grade the SOAP note.",
                key="case_file",
            )

            st.text_input(
                "📝 Case Title",
                placeholder="e.g., Patient Interview - Emergency Room",
                help="Used for downloads and grading reports.",
                key="case_title",
            )

            if uploaded_case is None:
                for key in [
                    "case_file_content",
                    "case_file_signature",
                    "auto_checklist",
                    "student_grade",
                    "final_soap_text",
                    "final_soap_signature",
                    "final_soap_name",
                    "final_soap_upload",
                ]:
                    st.session_state.pop(key, None)
                st.info("No case file attached. The app will run in SOAP-only mode.")
                return

            file_signature = f"{uploaded_case.name}:{getattr(uploaded_case, 'size', '')}"
            if st.session_state.get("case_file_signature") != file_signature:
                st.session_state.case_file_signature = file_signature
                for key in [
                    "case_file_content",
                    "auto_checklist",
                    "student_grade",
                    "final_soap_text",
                    "final_soap_signature",
                    "final_soap_name",
                    "final_soap_upload",
                ]:
                    st.session_state.pop(key, None)

            if not st.session_state.get('case_file_content'):
                with st.spinner("Processing case file..."):
                    try:
                        st.session_state.case_file_content = get_file_content(uploaded_case)
                        st.success("✅ Case file processed!")
                    except Exception as e:
                        st.error(f"Error processing case file: {e}")
                        st.session_state.case_file_content = ""

            st.success(f"✅ Case file uploaded: {uploaded_case.name}")
            if st.session_state.get('case_title'):
                st.caption(f"Reports will use the title: {st.session_state.case_title}")
