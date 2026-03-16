"""
Recording Components Module
Contains all recording-related UI components
"""
import os
import io
import time
import random
import string
import traceback
import re
import streamlit as st
import json
import streamlit.components.v1 as components
from datetime import datetime

from src.services.daily_service import (
    download_video,
    get_recording_download_link,
    list_recordings,
)


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
                def clean(seg):
                    return re.sub(r'[^a-z0-9-_]', '-', str(seg).lower()).strip('-_') or 'x'
                # Generate timestamp (UTC) in a readable format: YYYY-MM-DD_HH-MM-SS
                ts = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
                # Build room name: room__case(optional)__userid__datetime
                case_seg = clean(st.session_state.case_name) if st.session_state.get('case_name') else ""
                if case_seg:
                    full_name = f"{clean(base_room)}__{case_seg}__{clean(user_id)}__{ts}"
                else:
                    full_name = f"{clean(base_room)}__{clean(user_id)}__{ts}"
                st.session_state.room_name = full_name
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
        
        # Optional link if the embedded recorder is blocked

        components.html(
            f"""<iframe src='{iframe_url}' 
                width='100%' 
                height='450px'
                allow='microphone; camera; autoplay; display-capture'
                sandbox='allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation'></iframe>""",
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
        
    # Help section removed per UX request
    
    def process_recorded_audio(self):
        """Process cloud recording with resilient polling + fuzzy room name matching."""
        full_name = st.session_state.get('room_name')
        if not full_name:
            st.error("❌ No room name found.")
            return

        # Extract components; support both formats:
        # old: base__USERID__YYYYMMDDHHMMSS
        # new: base__CASENAME__USERID__YYYYMMDDHHMMSS
        parts = full_name.split('__')
        base = parts[0] if len(parts) > 0 else full_name
        if len(parts) >= 4:
            # new format
            case_name_part = parts[1]
            user_id = parts[2]
            ts = parts[3]
        else:
            case_name_part = ''
            user_id = parts[1] if len(parts) > 1 else ''
            ts = parts[2] if len(parts) > 2 else ''

        def norm(s:str):
            return re.sub(r'[^a-z0-9]', '', s.lower())

        norm_full = norm(full_name)
        token_base = norm(base)
        token_uid = norm(user_id)
        token_ts = norm(ts)

        # Generate variant prefixes to attempt startswith / contains matches
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

        max_attempts = int(os.getenv('DAILY_RECORDING_POLL_ATTEMPTS','18'))  # ~54s default at 3s
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
                        rn_norm = norm(rn)
                        # Quick variant match
                        variant_hit = any(v.lower() in rn.lower() or rn.lower().startswith(v.lower()) for v in variants)
                        # Token containment requirement: base and user id must appear (timestamp optional)
                        token_hit = token_base in rn_norm and token_uid in rn_norm
                        if variant_hit or token_hit:
                            # Score preference: exact full match > includes timestamp > tokens only
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
                    # Clear any previous outputs for a fresh auto-processing run
                    for k in ['soap_data','transcript','processing_started','processing_complete','interview_content','transcription_result','soap_result']:
                        if k in st.session_state:
                            del st.session_state[k]
                    # Jump straight to processing stage
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


class FileUploader:
    def render(self, on_analysis_start):
        """Improved file upload with better UX"""
        # Clear instructions
        st.markdown("**Drag and drop your file or click to browse:**")
        
        uploaded_file = st.file_uploader(
            label="Choose audio/video file",
            type=["mp3", "mp4", "m4a", "wav", "mov", "avi", "flv", "webm"],
            help="Supported formats: MP3, MP4, M4A, WAV, MOV, AVI, FLV, WEBM (max 200MB)",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            # Show file info
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.success(f"✅ **{uploaded_file.name}** uploaded successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📁 **File Size:** {file_size_mb:.1f} MB")
            with col2:
                st.info(f"📄 **Type:** {uploaded_file.type}")
            
            # Set session state
            st.session_state.encounter_file = uploaded_file
            st.session_state.interview_file = uploaded_file
            
            # Large, prominent button
            if st.button("🚀 Generate SOAP Note", type="primary", use_container_width=True):
                on_analysis_start()
        else:
            # Show helpful hints when no file is uploaded
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


class RecordingRetrieval:
    @st.cache_data(show_spinner=False)
    def _load_user_map(_self=None):
        """Load users.json and return a dict keyed by lowercase id -> user dict."""
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            users_path = os.path.join(base_dir, "config", "users.json")
            with open(users_path, "r", encoding="utf-8") as f:
                users = json.load(f)
            return {str(u.get("id", "")).lower(): u for u in users}
        except Exception:
            return {}

    def _get_current_user(self):
        """Return current user dict from session_state (or empty dict)."""
        return st.session_state.get('user') or {}

    @staticmethod
    def _parse_room_tokens(room_name: str):
        """Parse room name into (base, case, user, ts) supporting both old and new formats."""
        room_name = room_name or ''
        parts = room_name.split('__')
        base = parts[0] if len(parts) > 0 else ''
        if len(parts) >= 4:
            case = parts[1]
            user = parts[2]
            ts = parts[3]
        else:
            case = ''
            user = parts[1] if len(parts) > 1 else ''
            ts = parts[2] if len(parts) > 2 else ''
        return base, case, user, ts
    def render(self):
        """Retrieve a previous recording"""
        
        # Check recording API key
        daily_api_key = os.environ.get("DAILY_API_KEY", "")
        if not daily_api_key:
            st.error("⚠️ Cloud recording isn't configured.")
            return
        
        # CRITICAL: Check for download state FIRST. This is the main router.
        if st.session_state.get('downloading_recording'):
            # If the flag is set, execute the download process and stop rendering the search UI.
            self._execute_download_process()
            return
        
        # If not downloading, show the search interface.
        self._render_search_interface()

    def _render_search_interface(self):
        """Modern, centered search and results UI for recordings."""
    # Clean, inline search without extra header card

        # Centered search bar and button
        search_col1, search_col2 = st.columns([5,1])
        with search_col1:
            search_query = st.text_input(
                "Search recordings by room name",
                placeholder="Enter room name or part of it",
                label_visibility="collapsed"
            )
        with search_col2:
            search_clicked = st.button("🔍 Search", use_container_width=True)

    # No extra container closing since we removed the header card

        # Results area (always below search)
        if search_clicked and search_query:
            self.search_and_display_recordings(search_query)
        elif search_clicked:
            st.warning("Please enter a search term")

    
    def search_and_display_recordings(self, search_query):
        """Search for recordings matching the query and show as cards below search."""
        with st.spinner("🔍 Searching recordings..."):
            try:
                all_recordings = list_recordings()
                # Filter by current user for non-admin roles
                user = self._get_current_user()
                user_id = str(user.get('id', '')).strip()
                is_admin = str(user.get('role', '')).lower() == 'admin'
                def _norm(s: str):
                    import re as _re
                    return _re.sub(r'[^a-z0-9]', '', (s or '').lower())
                if not is_admin:
                    if user_id:
                        uid_norm = _norm(user_id)
                        filtered = []
                        for rec in all_recordings:
                            rn = rec.get('room_name', '')
                            _, _, rec_user, _ = self._parse_room_tokens(rn)
                            if _norm(rec_user) == uid_norm:
                                filtered.append(rec)
                        all_recordings = filtered
                    else:
                        # No user id -> show nothing for safety
                        all_recordings = []
                matching_recordings = [
                    rec for rec in all_recordings 
                    if search_query.lower() in rec.get('room_name', '').lower()
                ]
                st.markdown("<div style='height: 1.5em'></div>", unsafe_allow_html=True)
                if not matching_recordings:
                    st.warning(f"No recordings found matching '{search_query}'")
                    return
                st.markdown(f"<div style='text-align:center; color:#7fffa0; font-size:1.1em; margin-bottom:1em;'>Found {len(matching_recordings)} recording(s)</div>", unsafe_allow_html=True)
                for i, recording in enumerate(matching_recordings):
                    self._render_recording_card(recording, i, "use_rec")
            except Exception as e:
                st.error(f"Error searching recordings: {str(e)}")

    def _render_recording_card(self, recording, index, key_prefix):
        """Modern card-style result using Streamlit-native layout."""
        # Parse user id and timestamp from room_name
        room_name = recording.get('room_name', '') or ''
        parts = room_name.split('__')
        user_token = ''
        ts_token = ''
        if len(parts) >= 4:
            # base__case__user__ts
            user_token = parts[2]
            ts_token = parts[3]
        elif len(parts) >= 3:
            # base__user__ts
            user_token = parts[1]
            ts_token = parts[2]

        # Map user id to username via users.json
        user_map = self._load_user_map()
        user_info = user_map.get((user_token or '').lower())
        user_display = (user_info.get('username') if user_info else (user_token.upper() if user_token else 'Unknown'))

        # Format created from timestamp token or fallback to API field
        created_str = 'Unknown'
        ts_raw = ts_token or ''
        try:
            if ts_raw:
                # new format: YYYY-MM-DD_HH-MM-SS
                from datetime import datetime as _dt
                if len(ts_raw) == 19 and ts_raw[4] == '-' and ts_raw[7] == '-' and ts_raw[10] == '_' and ts_raw[13] == '-' and ts_raw[16] == '-':
                    created_str = _dt.strptime(ts_raw, '%Y-%m-%d_%H-%M-%S').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # old formats: YYYYMMDDHHMMSS or YYYYMMDD_HHMMSS
                    compact = ts_raw.replace('_', '')
                    if compact.isdigit() and len(compact) == 14:
                        created_str = _dt.strptime(compact, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
            if created_str == 'Unknown':
                st_time = recording.get('start_time')
                if isinstance(st_time, (int, float)):
                    from datetime import datetime as _dt
                    created_str = _dt.fromtimestamp(st_time).strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(st_time, str):
                    s = st_time.strip()
                    if s.isdigit():
                        from datetime import datetime as _dt
                        created_str = _dt.fromtimestamp(int(s)).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        created_str = s or 'Unknown'
        except Exception:
            pass

        with st.container(border=True):
            top_cols = st.columns([5,1])
            with top_cols[0]:
                st.markdown(
                    f"**Recording {index+1}:** {recording.get('room_name', 'Unknown')}"
                )
                st.caption(
                    f"Duration: {recording.get('duration', 'Unknown')} sec  •  Created: {created_str}  •  User: {user_display}"
                )
            with top_cols[1]:
                st.button(
                    "Use",
                    key=f"{key_prefix}_{index}_{recording.get('id', 'unknown')}",
                    on_click=self._prepare_for_download,
                    args=(recording,),
                    use_container_width=True,
                    help="Use this recording for analysis."
                )

    # Removed list_all_recordings feature by request
    
    def _render_recording_item(self, recording, index, key_prefix):
        """Render a single recording item. Clicking the button uses the on_click callback."""
        with st.expander(f"Recording {index+1}: {recording.get('room_name', 'Unknown')}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Room:** {recording.get('room_name', 'Unknown')}")
                st.write(f"**Duration:** {recording.get('duration', 'Unknown')} seconds")
                st.write(f"**Created:** {recording.get('start_time', 'Unknown')}")
                st.write(f"**ID:** {recording.get('id', 'Unknown')}")
                
            with col2:
                button_key = f"{key_prefix}_{index}_{recording.get('id', 'unknown')}"
                st.button(
                    f"📥 Use Recording {index+1}", 
                    key=button_key, 
                    on_click=self._prepare_for_download,
                    args=(recording,),
                    use_container_width=True
                )

    def _prepare_for_download(self, recording):
        """Callback function to set state before the rerun."""
        st.session_state.downloading_recording = True
        st.session_state.current_recording = recording

    def _execute_download_process(self):
        """This function handles the actual download and processing logic."""
        recording = st.session_state.get('current_recording')
        if not recording:
            st.error("No recording selected.")
            st.session_state.downloading_recording = False
            st.rerun()
            return

        details = []  # collect technical steps for optional display
        try:
            with st.spinner("Preparing your recording for analysis…"):
                recording_id = recording.get('id')
                room_name = recording.get('room_name')
                details.append(f"Recording ID: {recording_id}")
                details.append(f"Room Name: {room_name}")

                if not recording_id:
                    raise ValueError("Missing recording ID")

                # Get download link
                download_url = get_recording_download_link(recording_id)
                if not download_url:
                    raise RuntimeError("Failed to obtain download link")
                details.append("Obtained download URL")

                # Download file
                video_path = download_video(download_url)
                if not video_path or not os.path.exists(video_path):
                    raise RuntimeError("Download failed or file missing")
                details.append(f"Downloaded file to: {video_path}")

                # Load into session (no user-facing tech noise)
                with open(video_path, 'rb') as f:
                    video_content = f.read()
                    video_bytes = io.BytesIO(video_content)
                    video_bytes.name = f"{room_name or 'recording'}.mp4"
                    video_bytes.type = "audio/mp4"

                st.session_state.interview_file = video_bytes
                # Clear previous outputs
                for k in ['soap_data','transcript','processing_started','processing_complete','interview_content','transcription_result','soap_result']:
                    if k in st.session_state:
                        del st.session_state[k]
                # Start processing immediately
                st.session_state.processing_started = True
                st.session_state.workflow_stage = "processing"

                if os.path.exists(video_path):
                    os.unlink(video_path)
                details.append("Temporary file removed")

            # Outside spinner – single, friendly confirmation
            st.success("Recording ready. Starting analysis…")

            with st.expander("Details (optional)"):
                for line in details:
                    st.write(line)

            # Reset transient flags & redirect
            st.session_state.downloading_recording = False
            st.session_state.current_recording = None
            time.sleep(0.5)
            st.rerun()

        except Exception as e:
            st.error("Couldn't prepare the recording. Please try again.")
            with st.expander("Error details"):
                st.write(str(e))
                st.code(traceback.format_exc())
            st.session_state.downloading_recording = False
            st.session_state.current_recording = None
            # Allow user to retry without immediate rerun so they can read message
