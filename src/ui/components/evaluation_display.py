import json

import pandas as pd
import streamlit as st

from src.services.evaluation_service import checklist_counts, grade_final_soap_note
from src.utils.file_utils import get_file_content
from src.utils.pdf_generator import create_checklist_pdf, create_student_grade_pdf


class ChecklistDisplay:
    def render(self):
        checklist = st.session_state.get("auto_checklist") or []
        if not checklist:
            st.info("Checklist is generated automatically from the interview transcript.")
            return

        counts = checklist_counts(checklist)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Yes", counts["Yes"])
        with col2:
            st.metric("Partial", counts["Partial"])
        with col3:
            st.metric("No", counts["No"])
        with col4:
            st.metric("Total", len(checklist))

        st.dataframe(pd.DataFrame(checklist), use_container_width=True)

        pdf_bytes = create_checklist_pdf(checklist)
        json_bytes = json.dumps(checklist, indent=2).encode("utf-8")
        file_stub = st.session_state.get("case_title", "session").replace(" ", "_") or "session"

        col_left, col_right = st.columns(2)
        with col_left:
            st.download_button(
                "📥 Download Checklist PDF",
                data=pdf_bytes,
                file_name=f"{file_stub}_checklist.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_right:
            st.download_button(
                "📥 Download Checklist JSON",
                data=json_bytes,
                file_name=f"{file_stub}_checklist.json",
                mime="application/json",
                use_container_width=True,
            )


class GradeDisplay:
    def render(self):
        uploaded_final_soap = st.file_uploader(
            "📄 Upload Completed SOAP Note",
            type=["txt", "docx", "pdf"],
            help="Upload the completed SOAP note that should be graded.",
            key="final_soap_upload",
        )

        if uploaded_final_soap is not None:
            file_signature = f"{uploaded_final_soap.name}:{getattr(uploaded_final_soap, 'size', '')}"
            if st.session_state.get("final_soap_signature") != file_signature:
                st.session_state.final_soap_signature = file_signature
                st.session_state.final_soap_name = uploaded_final_soap.name
                st.session_state.final_soap_text = get_file_content(uploaded_final_soap) or ""
                st.session_state.pop("student_grade", None)

        final_soap_text = (st.session_state.get("final_soap_text") or "").strip()
        if not final_soap_text:
            st.info("Upload the completed SOAP note to unlock grading.")
            return

        st.markdown("#### Final SOAP Note Preview")
        st.text_area(
            "Uploaded SOAP Note",
            value=final_soap_text,
            height=260,
            disabled=True,
            key="final_soap_preview",
        )

        if st.button("🧮 Grade Final SOAP Note", type="primary", use_container_width=True):
            with st.spinner("Grading final SOAP note..."):
                st.session_state.student_grade = grade_final_soap_note(
                    final_soap_text,
                    st.session_state.get("transcript", ""),
                )

        student_grade = st.session_state.get("student_grade") or {}
        if not student_grade:
            st.caption("Run grading after uploading the completed SOAP note.")
            return

        criteria = student_grade.get("criteria") or []
        top_assessment = student_grade.get("assessment") or (criteria[0].get("Assessment") if criteria else "")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Assessment", top_assessment or "N/A")
        with col2:
            st.metric("Achieved Score", student_grade.get("achieved_score", ""))
        with col3:
            st.metric("Total Possible", student_grade.get("total_possible_score", ""))

        if student_grade.get("evaluation_summary"):
            st.markdown("#### Summary")
            st.write(student_grade["evaluation_summary"])

        if student_grade.get("detailed_llm_reasoning"):
            with st.expander("Detailed Reasoning"):
                st.write(student_grade["detailed_llm_reasoning"])

        if criteria:
            st.markdown("#### Criteria")
            st.dataframe(pd.DataFrame(criteria), use_container_width=True)

        pdf_bytes = create_student_grade_pdf(student_grade)
        json_bytes = json.dumps(student_grade, indent=2).encode("utf-8")
        file_stub = st.session_state.get("case_title", "session").replace(" ", "_") or "session"

        col_left, col_right = st.columns(2)
        with col_left:
            st.download_button(
                "📥 Download Grade PDF",
                data=pdf_bytes,
                file_name=f"{file_stub}_grade.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_right:
            st.download_button(
                "📥 Download Grade JSON",
                data=json_bytes,
                file_name=f"{file_stub}_grade.json",
                mime="application/json",
                use_container_width=True,
            )
