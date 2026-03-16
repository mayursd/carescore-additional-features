"""
Live Recorder UI component
"""
import os
import time
import io
import traceback
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from src.services.daily_service import (
    download_video,
    get_recording_download_link,
    list_recordings,
)
from .utils import build_room_name, normalize_token


class LiveRecorder:
    def render(self):
        """Improved live recorder with better UX"""
        # Check API key first
        daily_api_key = os.environ.get("DAILY_API_KEY", "")
        if not daily_api_key:
            st.error("⚠️ Live recording isn't configured.")
            st.info("💡 **Alternative:** Use the 'Upload File' option instead.")
            return

        st.markdown("**Step 1: Create your event**")

        # Inline layout: dropdown + action
        col_inp, col_btn = st.columns([4, 1])
        with col_inp:
            room_options = [
                # EEC rooms
                "EEC - A","EEC - B","EEC - C","EEC - D","EEC - E","EEC - F",
                "EEC - G","EEC - H","EEC - I","EEC - J","EEC - K","EEC - L",
                "EEC - M","EEC - N",
                # IPEC rooms
                "IPEC - 1","IPEC - 2","IPEC - 3","IPEC - 4","IPEC - 5","IPEC - 6 Theater",
            ]
            sentinel = "Select a room"
            display_options = [sentinel] + room_options
            prev = st.session_state.get('base_room_name')
            try:
                default_index = display_options.index(prev) if prev else 0
            except ValueError:
                default_index = 0
            selected_room = st.selectbox(
                "Room *",
                options=display_options,
                index=default_index,
                help="We'll add a short code and time to keep it unique",
                key="base_room_select",
            )
        with col_btn:
            create_clicked = st.button(
                "Create Event",
                type="primary",
                use_container_width=True,
            )
        # Optional case name field (full width)
        case_name = st.text_input(
            "Case name (optional)",
            value=st.session_state.get('case_name', ''),
            placeholder="e.g., OSCE - Respiratory, Case 3",
        )
        if create_clicked:
            # Validate input at click time so the button is always enabled
            base_room = selected_room if selected_room != sentinel else ""
            if not base_room or not base_room.strip():
                st.warning("Please select a room.")
            else:
                st.session_state.base_room_name = base_room
                # Persist optional case name
                st.session_state.case_name = (case_name or "").strip()
                user = st.session_state.get('user') or {}
                user_id = user.get('id', 'UID')
                # Compose canonical room name using shared util
                st.session_state.room_name = build_room_name(base_room, st.session_state.get('case_name'), user_id)
                st.rerun()

        # Show the interface if room name is provided
        if st.session_state.get('room_name'):
            st.success(f"✅ Event created: **{st.session_state.room_name}**")

            st.markdown("**Step 2: Start your recording**")

            # Instructions
            st.info("""
            🎥 **Recording Instructions:**
            1. Allow microphone/camera permissions when prompted
            2. Conduct your clinical interview (start/stop as needed)
            3. Click *Process Recording* once finished (auto processing will begin)
            """)

            self._render_recording_interface(daily_api_key)
        else:
            # Friendly guidance instead of warning
            st.markdown("""
            📝 **Get Started:**
            - Choose a room from the dropdown above
            - Click "Create Event" to continue
            """)
    
    def _render_recording_interface(self, daily_api_key):
        """Render the recording interface"""
        # Generate timestamp if needed
        if "recording_timestamp" not in st.session_state:
            # Local time, readable format: YYYY-MM-DD_HH-MM-SS
            st.session_state.recording_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Embed recorder (hosted)
        iframe_url = (
            f"https://s3.us-east-1.amazonaws.com/lofllc.com/main.html"
            f"?apikey={daily_api_key}"
            f"&roomName={st.session_state.room_name}"
            f"&timestamp={st.session_state.recording_timestamp}"
        )
        
        components.html(
            f"""<iframe src='{iframe_url}' 
                width='100%' 
                height='450px'
                allow='microphone; camera; autoplay; display-capture'
                sandbox='allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-popups-to-escape-sandbox allow-presentation'></iframe>""",
            height=450,
        )
        
        st.markdown("---")
        
        # Processing button (only show if we haven't already pulled the recording into interview_file)
        if not st.session_state.get('interview_file'):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🎵 Process Recording", type="primary", use_container_width=True):
                    self.process_recorded_audio()
        else:
            st.success("Recording file ready below – proceed to Start Processing.")
        
    def process_recorded_audio(self):
        """Process cloud recording with resilient polling + fuzzy room name matching."""
        full_name = st.session_state.get('room_name')
        if not full_name:
            st.error("❌ No room name found.")
            return

        parts = full_name.split('__')
        base = parts[0] if len(parts) > 0 else full_name
        if len(parts) >= 4:
            case_name_part = parts[1]
            user_id = parts[2]
            ts = parts[3]
        else:
            case_name_part = ''
            user_id = parts[1] if len(parts) > 1 else ''
            ts = parts[2] if len(parts) > 2 else ''

        # Normalize tokens for fuzzy matching
        norm_full = normalize_token(full_name)
        token_base = normalize_token(base)
        token_uid = normalize_token(user_id)
        token_ts = normalize_token(ts)

        variants = {
            full_name,
            full_name.lower(),
            full_name.replace('__','_'),
            full_name.replace('__','-'),
            full_name.replace('__',''),
            f"{base}-{user_id}-{ts}".lower(),
            f"{base}_{user_id}_{ts}".lower(),
        }
        variants = [v for v in variants if v]

        max_attempts = int(os.getenv('DAILY_RECORDING_POLL_ATTEMPTS','18'))
        interval = float(os.getenv('DAILY_RECORDING_POLL_INTERVAL','3'))
        attempt_box = st.empty()

        with st.spinner("🔍 Searching for recording (polling)..."):
            try:
                found = None
                last_batch = []
                for attempt in range(1, max_attempts+1):
                    all_recs = list_recordings()
                    last_batch = all_recs
                    scored = []
                    for rec in all_recs:
                        rn = rec.get('room_name','')
                        rn_norm = normalize_token(rn)
                        variant_hit = any(v.lower() in rn.lower() or rn.lower().startswith(v.lower()) for v in variants)
                        token_hit = token_base in rn_norm and token_uid in rn_norm
                        if variant_hit or token_hit:
                            score = 0
                            if rn_norm == norm_full: score += 100
                            if token_ts and token_ts in rn_norm: score += 30
                            if variant_hit: score += 10
                            if token_hit: score += 5
                            scored.append((score, rec))
                    if scored:
                        scored.sort(key=lambda x: (x[0], x[1].get('start_time',0)), reverse=True)
                        found = scored[0][1]
                        break
                    attempt_box.caption(f"Attempt {attempt}/{max_attempts}: not found yet – waiting {interval}s…")
                    time.sleep(interval)
                attempt_box.empty()

                if not found:
                    st.error(f"❌ No recordings found for room '{full_name}'.")
                    if st.session_state.get('debug_mode_toggle'):
                        st.write('Variants tried:', variants)
                        st.write('Sample recent names:', [r.get('room_name') for r in last_batch[:10]])
                    st.info("If you just stopped the recording, wait a few more seconds and click 'Process Recording' again.")
                    return

                st.success(f"✅ Found recording: {found.get('room_name','(unnamed)')}")

                with st.spinner("⬇️ Downloading recording..."):
                    rec_id = found.get('id')
                    if not rec_id:
                        st.error('Recording object missing id.')
                        return
                    download_url = get_recording_download_link(rec_id)
                    video_path = download_video(download_url)
                    if not video_path or not os.path.exists(video_path):
                        st.error('❌ Failed to download recording file.')
                        return
                    with open(video_path,'rb') as f:
                        vb = io.BytesIO(f.read())
                        vb.name = f"{full_name}_{st.session_state.recording_timestamp}.mp4"
                        vb.type = 'audio/mp4'
                    st.session_state.interview_file = vb
                    for k in ['soap_data','transcript','processing_started','processing_complete','interview_content','transcription_result','soap_result']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state.processing_started = True
                    st.session_state.workflow_stage = 'processing'
                    st.success('🎉 Recording captured. Starting analysis…')
                    time.sleep(0.5)
                    try:
                        os.unlink(video_path)
                    except Exception:
                        pass
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error processing recording: {e}")
                if st.session_state.get('debug_mode_toggle'):
                    st.code(traceback.format_exc())
