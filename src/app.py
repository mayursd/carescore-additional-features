import streamlit as st
import sys
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get the absolute path of the directory containing the current file (app.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (which is the project root)
project_root = os.path.dirname(current_dir)
# Add the project root to sys.path
sys.path.insert(0, project_root)
from src.ui.pages import Navigation, SessionState


st.set_page_config(
    page_title="CareScore AI",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="auto",
)

daily_api_key = os.environ.get("DAILY_API_KEY")

USERS_FILE = Path(project_root) / "src" / "config" / "users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        users = {u['username']: u for u in data if 'username' in u and 'password' in u}
        return users
    except Exception as e:
        st.error(f"Failed loading users.json: {e}")
        return {}

USERS = load_users()

class CareScoreAI:
    def __init__(self):
        self.session_state = SessionState()
        self.navigation = Navigation()

    def run(self):
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            self.show_login_page()
            return

        # Render header and sidebar
        self.navigation.render_header()
        selected = self.navigation.render_sidebar()
        # Show current user badge
        with st.sidebar:
            user = st.session_state.get('user') or {}
            st.caption(f"Logged in as: **{user.get('username','?')}** ({user.get('role','')})")
        # Render the main page
        self.navigation.pages[selected].render()

    def show_login_page(self):
        """Improved login page with better UX"""
        # Center the login form
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            # Logo and welcome message
            st.image("src/ui/assets/lof_logo.png", width=200)
            st.markdown("<h2 style='text-align: center; color: #2E8B57;'>Welcome to CareScore AI</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666; margin-bottom: 30px; font-size: 18px; font-weight: 500;'>🩺 Transforming Clinical Conversations into Structured Documentation</p>", unsafe_allow_html=True)
            
            # Login form
            with st.form("login_form"):
                st.markdown("### 🔐 Please Login")
                
                username = st.text_input(
                    "Username", 
                    placeholder="Enter your username",
                    help="Use your assigned CareScore username"
                )
                password = st.text_input(
                    "Password", 
                    type="password", 
                    placeholder="Enter your password",
                    help="Enter your secure password"
                )
                
                submitted = st.form_submit_button(
                    "🚀 Login", 
                    type="primary", 
                    use_container_width=True
                )
                
                if submitted:
                    user_rec = USERS.get(username)
                    if user_rec and user_rec.get('password') == password:
                        # Ensure an ID exists (fallback deterministic hash fragment if missing)
                        user_id = user_rec.get('id')
                        if not user_id:
                            import hashlib
                            user_id = 'U' + hashlib.sha1(user_rec.get('username','?').encode()).hexdigest()[:8].upper()
                            user_rec['id'] = user_id
                        st.session_state.authenticated = True
                        st.session_state.user = {
                            'username': user_rec.get('username'),
                            'role': user_rec.get('role', 'user'),
                            'id': user_id
                        }
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
            
            # Help section
            with st.expander("ℹ️ Need Help?"):
                st.markdown("**For access or issues contact:** admin@leapoffaith.com")
            
            # Footer
            st.markdown("---")
            st.caption("🔒 Secure clinical documentation platform")
            st.caption("© 2025 CareScore AI - All rights reserved")

        # Developer helper: show loaded users in debug mode
        if st.session_state.get('debug_mode'):
            st.write({ 'loaded_users': list(USERS.keys()) })


if __name__ == "__main__":
    app = CareScoreAI()
    app.run()
