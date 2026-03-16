"""
Recording Retrieval UI component
"""
import os
import io
import time
import json
import traceback
import streamlit as st

from src.services.daily_service import (
    download_video,
    get_recording_download_link,
    list_recordings,
)


class RecordingRetrieval:
    @st.cache_data(show_spinner=False)
    def _load_user_map(_self=None):
        """Load users.json and return a dict keyed by lowercase id -> user dict."""
        try:
            # __file__ is src/ui/components/recording/recording_retrieval.py
            # repo root -> src -> ui -> components -> recording -> (this file)
            # users.json lives at src/config/users.json
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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
        search_col1, search_col2 = st.columns([5,1])
        with search_col1:
            search_query = st.text_input(
                "Search recordings by room name",
                placeholder="Enter room name or part of it",
                label_visibility="collapsed"
            )
        with search_col2:
            search_clicked = st.button("🔍 Search", use_container_width=True)

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
        room_name = recording.get('room_name', '') or ''
        parts = room_name.split('__')
        user_token = ''
        ts_token = ''
        if len(parts) >= 4:
            user_token = parts[2]
            ts_token = parts[3]
        elif len(parts) >= 3:
            user_token = parts[1]
            ts_token = parts[2]

        user_map = self._load_user_map()
        user_info = user_map.get((user_token or '').lower())
        user_display = (user_info.get('username') if user_info else (user_token.upper() if user_token else 'Unknown'))

        created_str = 'Unknown'
        ts_raw = ts_token or ''
        try:
            if ts_raw:
                from datetime import datetime as _dt
                if len(ts_raw) == 19 and ts_raw[4] == '-' and ts_raw[7] == '-' and ts_raw[10] == '_' and ts_raw[13] == '-' and ts_raw[16] == '-':
                    created_str = _dt.strptime(ts_raw, '%Y-%m-%d_%H-%M-%S').strftime('%Y-%m-%d %H:%M:%S')
                else:
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

        details = []
        try:
            with st.spinner("Preparing your recording for analysis…"):
                recording_id = recording.get('id')
                room_name = recording.get('room_name')
                details.append(f"Recording ID: {recording_id}")
                details.append(f"Room Name: {room_name}")

                if not recording_id:
                    raise ValueError("Missing recording ID")

                download_url = get_recording_download_link(recording_id)
                if not download_url:
                    raise RuntimeError("Failed to obtain download link")
                details.append("Obtained download URL")

                video_path = download_video(download_url)
                if not video_path or not os.path.exists(video_path):
                    raise RuntimeError("Download failed or file missing")
                details.append(f"Downloaded file to: {video_path}")

                with open(video_path, 'rb') as f:
                    video_content = f.read()
                    video_bytes = io.BytesIO(video_content)
                    video_bytes.name = f"{room_name or 'recording'}.mp4"
                    video_bytes.type = "audio/mp4"

                st.session_state.interview_file = video_bytes
                for k in ['soap_data','transcript','processing_started','processing_complete','interview_content','transcription_result','soap_result']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.processing_started = True
                st.session_state.workflow_stage = "processing"

                if os.path.exists(video_path):
                    os.unlink(video_path)
                details.append("Temporary file removed")

            st.success("Recording ready. Starting analysis…")

            with st.expander("Details (optional)"):
                for line in details:
                    st.write(line)

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
