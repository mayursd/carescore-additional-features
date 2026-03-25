"""
Results Display Components
Contains components for displaying analysis results
"""
import streamlit as st
import json
import hashlib
from typing import Optional
from st_copy_to_clipboard import st_copy_to_clipboard


# ---------- Helpers (AI Plan) ----------

def _normalize_ap_dict(ap_in: Optional[dict]) -> dict:
    ap_in = ap_in or {}
    return {
        "Final_diagnosis": ap_in.get("Final_diagnosis", ""),
        "Investigations": ap_in.get("Investigations", ""),
        "Medications": ap_in.get("Medications", ""),
        "Education": ap_in.get("Education", "") or ap_in.get("Pt_Education", ""),
        "Follow_Up": ap_in.get("Follow_Up", ""),
        "Referrals": ap_in.get("Referrals", "") or ap_in.get("Consults", ""),
        "Disposition": ap_in.get("Disposition", ""),
        "Other": ap_in.get("Other", "")
    }

def _format_ai_plan_text(ai_dict: dict) -> str:
    """Render exactly like the DOCX formatting, filling 'Not documented' for blanks."""
    def nz(s: str) -> str:
        s = (s or "").strip()
        return s if s else "Not documented"

    lines = [
        f"Final diagnosis or problems(s): {nz(ai_dict.get('Final_diagnosis'))}",
        f"Investigations: {nz(ai_dict.get('Investigations'))}",
        f"Medications: {nz(ai_dict.get('Medications'))}",
        f"Education: {nz(ai_dict.get('Education'))}",
        f"Follow-Up: {nz(ai_dict.get('Follow_Up'))}",
        f"Referrals/Consults: {nz(ai_dict.get('Referrals'))}",
        f"Disposition: {nz(ai_dict.get('Disposition'))}",
        f"Other: {nz(ai_dict.get('Other'))}",
    ]
    return "\n".join(lines)

def _ai_sig(transcript_txt: str, ap_dict: dict) -> str:
    payload = json.dumps({"t": transcript_txt or "", "ap": ap_dict or {}},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _has_meaningful_encounter(transcript_txt: str, soap_data: Optional[dict]) -> bool:
    """
    Return True if transcript/SOAP contain real clinical content.

    Heuristics:
      - transcript length beyond trivial 'recording' stub
      - any SOAP fields not 'Not mentioned'/'Not documented'/empty
    """
    t = (transcript_txt or "").strip().lower()
    if t:
        # very short or "recording" stubs are not meaningful
        if len(t) > 80 and "recording" not in t:
            return True

    if isinstance(soap_data, dict):
        # scan for any non-empty, non-'not mentioned/documented' values
        canon_empty = {"not mentioned", "not documented", ""}
        for _, val in soap_data.items():
            if isinstance(val, dict):
                for __, v in val.items():
                    if isinstance(v, str) and v.strip().lower() not in canon_empty:
                        return True
            elif isinstance(val, str):
                if val.strip().lower() not in canon_empty:
                    return True
    return False


# 🔁 Cache builder so we don't rebuild the DOCX on every rerun unless inputs change
@st.cache_data(show_spinner=False)
def _build_docx_bytes_cached(soap_text: str, interview_text: str, template_path: str):
    if not (soap_text.strip() or interview_text.strip()):
        return None
    from src.services.soap_service import populate_soap_template, parse_soap_text_to_dict
    parsed_soap = parse_soap_text_to_dict(soap_text) if soap_text.strip() else {}

    # ✅ Only enable AI suggestions in DOCX when there's meaningful content
    ai_allowed = _has_meaningful_encounter(interview_text, parsed_soap)

    return populate_soap_template(
        template_file=template_path,
        transcript=interview_text,
        soap_data=parsed_soap,
        ai_suggestions_enabled=ai_allowed,     # was True
        use_ai_assessment_plan=ai_allowed      # was True
    )


class SoapNoteDisplay:
    def render(self):
        # ---------- Prepare transcript & SOAP ----------
        interview_content = st.session_state.get("interview_content", {})
        transcript_txt = (
            interview_content.get("interview", "")
            if isinstance(interview_content, dict)
            else str(interview_content)
        ).strip()
        if not transcript_txt:
            transcript_txt = (st.session_state.get("transcript", "") or "").strip()

        soap_data = st.session_state.get("soap_data")
        ap_norm = _normalize_ap_dict(soap_data.get("Assessment_Plan") if soap_data else {})

        # Compute signature for transcript + AP to detect changes
        sig = _ai_sig(transcript_txt, ap_norm)

        # ---------- Auto-extract SOAP if missing ----------
        if not soap_data and transcript_txt:
            try:
                from src.services.soap_service import extract_soap_data
                extracted = extract_soap_data(transcript_txt, current_texts=None)
                if extracted and "soap_data" in extracted and extracted["soap_data"]:
                    st.session_state["soap_data"] = extracted["soap_data"]
                    soap_data = st.session_state["soap_data"]
            except Exception as e:
                st.warning(f"Could not auto-extract SOAP from transcript: {e}")

        # ---------- Generate AI plan if missing or changed ----------
        ai_plan = st.session_state.get("ai_plan")
        if not ai_plan or st.session_state.get("ai_plan_sig") != sig:
            try:
                from src.services.soap_service import generate_ai_assessment_plan


                if _has_meaningful_encounter(transcript_txt, soap_data):
                    ai_dict = generate_ai_assessment_plan(transcript_txt, ap_norm) or {}
                    ai_plan = _format_ai_plan_text(ai_dict) if ai_dict else ""

                else:
                        # ✅ When there is no meaningful data, set the AI plan to 'Not documented'
                    ai_plan = "\n".join([
                        "Final diagnosis or problems(s): Not documented",
                        "Investigations: Not documented",
                        "Medications: Not documented",
                        "Education: Not documented",
                        "Follow-Up: Not documented",
                        "Referrals/Consults: Not documented",
                        "Disposition: Not documented",
                        "Other: Not documented",
                    ])

                st.session_state["ai_plan"] = ai_plan
                st.session_state["ai_plan_sig"] = sig

                # Inject AI plan into SOAP data for downstream consumers
                if soap_data:
                    ap = soap_data.get("Assessment_Plan") or {}
                    ap["AI_Plan"] = ai_plan
                    soap_data["Assessment_Plan"] = ap
                    st.session_state["soap_data"] = soap_data

            except Exception as e:
                # Quiet failure (no banner about "missing generator")
                st.warning(f"Could not generate AI Assessment & Plan: {e}")

        if not soap_data:
            st.warning("⚠️ SOAP data not available. Please run the processing pipeline first.")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_event(f"SoapNoteDisplay render END at {end_time.strftime('%Y-%m-%d %H:%M:%S')} | duration: {duration:.2f} seconds")
            return

        # ---------- Render editor and actions ----------
        # Initialize editor if missing
        if not st.session_state.get("soap_note"):
            st.session_state["soap_note"] = self._generate_full_soap_text(soap_data)

        # Header: title + copy button
        header_left, header_right = st.columns([1, 0.25])
        with header_left:
            st.markdown("#### 📄 SOAP Note")
        with header_right:
            st_copy_to_clipboard(
                text=st.session_state.get("soap_note", ""),
                before_copy_label="📋 Copy All",
                after_copy_label="✅ Copied!",
                key="copy_all_soap_top",
            )

        # Editable text area
        st.text_area(
            "SOAP Note (editable)",
            height=500,
            key="soap_note",
            on_change=self._sync_soap_text_to_data,
        )

        # === Side-by-side Save (left) and Generate & Download (right) ===
        left_btn_col, right_btn_col = st.columns([1, 1])

        with left_btn_col:
            if st.button("💾 Save SOAP Note", use_container_width=True):
                # Content already persisted in st.session_state["soap_note"]
                st.success("SOAP note saved.")

        with right_btn_col:
            template_path = "src/templates/SOAP_Note_Template.docx"
            soap_bytes = None
            try:
                from src.services.soap_service import populate_soap_template

                if soap_data and transcript_txt:
                    soap_bytes = populate_soap_template(
                        template_file=template_path,
                        transcript=transcript_txt,
                        soap_data=soap_data,
                        ai_suggestions_enabled=False,
                        use_ai_assessment_plan=False
                    )
            except Exception as e:
                st.warning(f"Could not generate DOCX for download: {e}")

            file_name = f"{st.session_state.get('case_title','session').replace(' ','_')}_SOAP.docx"
            st.download_button(
                label="📥Download SOAP Note (DOCX)",
                data=soap_bytes if soap_bytes else b"",
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary",
                disabled=(soap_bytes is None),
            )
            if soap_bytes is None:
                st.info("Add a SOAP note or transcript to enable download.")

            st.markdown("---")


    def _sync_soap_text_to_data(self):
        """Parse the current text area back into soap_data so downstream stays consistent."""
        try:
            from src.services.soap_service import parse_soap_text_to_dict
            soap_text = st.session_state.get("soap_note", "") or ""
            parsed = parse_soap_text_to_dict(soap_text)

            # Preserve any previously generated AI plan if parser didn't capture it
            existing_ai = st.session_state.get("ai_plan", "")
            if existing_ai and not (parsed.get("Assessment_Plan", {}) or {}).get("AI_Plan"):
                ap = parsed.get("Assessment_Plan") or {}
                ap["AI_Plan"] = existing_ai
                parsed["Assessment_Plan"] = ap

            st.session_state["soap_data"] = parsed
        except Exception as e:
            st.warning(f"Could not sync SOAP text to data: {e}")

    def _generate_full_soap_text(self, soap_data):
        """Generate formatted text of entire SOAP note (now includes AI-Based A&P last)"""
        soap_sections = []

        # Subjective Section
        soap_sections.append("=== SUBJECTIVE ===")
        soap_sections.append("")

        # HPI
        soap_sections.append("History of Present Illness (HPI):")
        soap_sections.append(soap_data.get("HPI", "Not documented"))
        soap_sections.append("")

        # PMHx
        soap_sections.append("Past Medical History:")
        soap_sections.append(soap_data.get("PMHx", "Not documented"))
        soap_sections.append("")

        # Medications
        soap_sections.append("Medications:")
        soap_sections.append(soap_data.get("Medications", "Not documented"))
        soap_sections.append("")

        # Family History
        soap_sections.append("Family History:")
        soap_sections.append(soap_data.get("FHx", "Not documented"))
        soap_sections.append("")

        # Allergies
        soap_sections.append("Allergies:")
        soap_sections.append(soap_data.get("Allergies", "Not documented"))
        soap_sections.append("")

        # Social History
        soap_sections.append("Social History:")
        if isinstance(soap_data.get("SHx"), dict):
            shx_text = "\n".join(
                [f"{k}: {v}" for k, v in soap_data["SHx"].items() if v is not None]
            )
        else:
            shx_text = str(soap_data.get("SHx", "Not documented"))
        soap_sections.append(shx_text)
        soap_sections.append("")

        # Review of Systems
        soap_sections.append("Review of Systems:")
        if isinstance(soap_data.get("Review_of_Systems"), dict):
            ros_text = "\n".join(
                [f"{k}: {v}" for k, v in soap_data["Review_of_Systems"].items() if v is not None]
            )
        else:
            ros_text = str(soap_data.get("Review_of_Systems", "Not documented"))
        soap_sections.append(ros_text)
        soap_sections.append("")

        # Objective Section
        soap_sections.append("=== OBJECTIVE ===")
        soap_sections.append("")
        soap_sections.append("Physical Exam:")
        if isinstance(soap_data.get("Objective"), dict):
            obj_text = "\n".join(
                [f"{k}: {v}" for k, v in soap_data["Objective"].items() if v is not None]
            )
        else:
            obj_text = str(soap_data.get("Objective", "Not documented"))
        soap_sections.append(obj_text)
        soap_sections.append("")

        # Assessment & Plan Section
        soap_sections.append("=== ASSESSMENT & PLAN ===")
        soap_sections.append("")
        ap = soap_data.get("Assessment_Plan", {}) or {}
        if isinstance(ap, dict):
            lines = []
            for label, key_opts in [
                ("Final_diagnosis", ["Final_diagnosis"]),
                ("Investigations", ["Investigations"]),
                ("Medications", ["Medications"]),
                ("Education", ["Education", "Pt_Education"]),
                ("Follow-Up", ["Follow_Up"]),
                ("Referrals/Consults", ["Referrals", "Consults"]),
                ("Disposition", ["Disposition"]),
                ("Other", ["Other"]),
            ]:
                val = ""
                for k in key_opts:
                    if ap.get(k):
                        val = ap.get(k, "")
                        break
                lines.append(f"{label}: {val if val != '' else 'Not documented'}")

            # 🔹 Append AI-based Assessment & Plan block LAST (always render)
            ai_plan_text = (ap.get("AI_Plan") or "").strip()
            lines.append("")  # spacing
            lines.append("AI-Based Assessment & Plan:")
            if ai_plan_text:
                lines.append(ai_plan_text)
            else:
                # default fallback makes the emptiness explicit
                lines.append("Final diagnosis or problems(s): Not documented")
                lines.append("Investigations: Not documented")
                lines.append("Medications: Not documented")
                lines.append("Education: Not documented")
                lines.append("Follow-Up: Not documented")
                lines.append("Referrals/Consults: Not documented")
                lines.append("Disposition: Not documented")
                lines.append("Other: Not documented")

            ap_text = "\n".join(lines)
        else:
            ap_text = str(ap or "Not documented")
        soap_sections.append(ap_text)

        # Combine all sections
        return "\n".join(soap_sections)


class TranscriptDisplay:
    def render(self):
        """Display transcript"""
        transcript = st.session_state.get("transcript", "")

        # precompute transcript from interview_content if not already present
        if not transcript and st.session_state.get("interview_content"):
            st.session_state.transcript = (
                st.session_state.interview_content.get("interview", "")
                if isinstance(st.session_state.interview_content, dict)
                else str(st.session_state.interview_content)
                )
            transcript = st.session_state.transcript
        if not transcript:
            st.warning("⚠️ No transcript available")
            return

        st.markdown("### 🎙️ Transcript")

        # Search functionality
        search_term = st.text_input("🔍 Search transcript", placeholder="Enter search term", key="transcript_search")

        # Display transcript
        if search_term:
            # Highlight search terms
            highlighted_transcript = self._highlight_text(transcript, search_term)
            st.markdown(highlighted_transcript, unsafe_allow_html=True)
        else:
            st.text_area(
                "Transcript content",
                value=transcript,
                height=400,
                disabled=True,
                key="transcript_text_area"
            )

        # One-click download
        st.download_button(
            label="📥 Download Transcript (.txt)",
            data=transcript,
            file_name="interview_transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )

    def _highlight_text(self, text, search_term):
        """Highlight search terms in text"""
        if not search_term:
            return text

        import re
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        highlighted = pattern.sub(f"<mark>{search_term}</mark>", text)
        return f"<div style='white-space: pre-wrap;'>{highlighted}</div>"


class ResultsSummary:
    def render(self):
        """Display results summary"""
        st.markdown("### 📊 Analysis Summary")

        # Check what results we have
        has_soap = bool(st.session_state.get("soap_data"))
        has_transcript = bool(st.session_state.get("transcript"))
        has_checklist = bool(
            st.session_state.get("auto_checklist")
            or st.session_state.get("transcript_checklist")
            or st.session_state.get("manual_checklist")
        )
        has_grade = bool(st.session_state.get("student_grade"))

        columns = st.columns(4)

        with columns[0]:
            if has_soap:
                st.success("✅ SOAP Note Complete")
            else:
                st.error("❌ No SOAP Note")

        with columns[1]:
            if has_transcript:
                st.success("✅ Transcript Complete")
            else:
                st.error("❌ No Transcript")

        with columns[2]:
            if has_checklist:
                st.success("✅ Checklist Complete")
            else:
                st.info("ℹ️ Checklist Pending")

        with columns[3]:
            if has_grade:
                st.success("✅ Grading Complete")
            elif st.session_state.get("final_soap_text"):
                st.warning("⏳ Grade Pending")
            else:
                st.info("ℹ️ Upload Final SOAP")

    
