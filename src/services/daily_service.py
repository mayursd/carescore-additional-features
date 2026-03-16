import os
import requests
import streamlit as st
import tempfile


# Daily API integration
DAILY_API_KEY = os.environ.get("DAILY_API_KEY", "")


def get_recording_download_link(recording_id: str, valid_secs: int = 3600) -> str:
    """Get a download link for a Daily recording."""
    url = f"https://api.daily.co/v1/recordings/{recording_id}/access-link?valid_for_secs={valid_secs}"
    
    # Use API key from session state or environment variable
    api_key = getattr(st.session_state, 'daily_api_key', None) or DAILY_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Daily API error: {response.json().get('error', 'Unknown error')}")

    result = response.json()
    download_url = result.get("download_link")
    if not download_url or "http" not in download_url:
        raise Exception("Invalid or missing download URL.")
    return download_url


def download_video(download_url: str) -> str:
    """Download a video from a URL and return the local file path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                temp_file.write(chunk)
        return temp_file.name

def list_recordings():
    """List all available Daily.co recordings."""
    url = "https://api.daily.co/v1/recordings"
    
    # Use API key from session state or environment variable
    api_key = getattr(st.session_state, 'daily_api_key', None) or DAILY_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Daily API error: {response.json().get('error', 'Unknown error')}")
    response_data = response.json()
    return response_data.get("data", [])