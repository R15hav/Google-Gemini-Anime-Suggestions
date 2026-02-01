import streamlit as st
import requests
import time
from datetime import datetime, timedelta

# 1. Initialize Session State
if "last_free_request" not in st.session_state:
    st.session_state.last_free_request = None

def check_cooldown():
    """Returns (True, remaining_seconds) if currently in cooldown."""
    if st.session_state.last_free_request is None:
        return False, 0
    
    elapsed = datetime.now() - st.session_state.last_free_request
    if elapsed < timedelta(hours=1):
        return True, 3600 - elapsed.total_seconds()
    return False, 0

# Set page configuration
st.set_page_config(page_title="Anime Sensei", page_icon="🏯", layout="centered")

st.title("🏯 Anime Sensei: Gemini Recommender")
st.markdown("Discover your next favorite anime based on your AniList history.")

# Sidebar for Configuration
with st.sidebar:
    st.header("🔑 Authentication")
    # 1. Secure Input Field
    user_api_key = st.text_input(
        "Enter Gemini API Key", 
        type="password", 
        help="Get your free key at aistudio.google.com"
    )
    st.info("Your key is used only for this session and never stored.")

    st.header("⚙️ Settings")
    username = st.text_input("AniList Username", placeholder="e.g., your_username")
    
    # Model Choice Dropdown
    model_choice = st.selectbox(
        "Select Gemini Model",
        options=["gemini-2.5-flash-lite",
                "gemini-3-pro-preview",
                "gemini-3-flash-preview",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite"],
        index=0,
        help="Pro is better for deep reasoning; Flash is faster."
    )
    
    st.divider()
    st.info("Tip: Make sure your AniList profile is public!")

# 2. Determine Button State
is_locked, time_left = check_cooldown()

# Unlock automatically if they provide their own key
if user_api_key:
    is_locked = False
    button_label = "Get Recommendations (Premium)"
elif is_locked:
    mins = int(time_left // 60)
    button_label = f"Wait {mins} min for next free request"
else:
    button_label = "Get Recommendations (Free Tier)"

# Main UI Logic
if st.button(button_label, disabled=(is_locked and not user_api_key), type="primary"):
    
    if not username:
        st.warning("Please enter an AniList username first.")
    else:
        if not user_api_key:
            st.warning("⚠️ Suggesting with limited capabilities (no API key).")

        with st.spinner(f"Analyzing {username}'s taste with {model_choice}..."):
            try:
                # Replace with your actual FastAPI production URL after hosting
                backend_url = f"http://localhost:8000/recommend/{username}"
                headers = {"x-gemini-api-key": user_api_key}
                payload = {"model_choice": model_choice}
                
                response = requests.get(backend_url, params=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    st.success("Analysis Complete!")
                    #st.subheader(f"👤 Persona: {data.get('persona', 'Anime Enthusiast')}")

                    # Display Recommendations in clean cards
                    for rec in data:
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"### {rec['title']}")
                                st.write(rec['reason'])
                            with col2:
                                st.metric("Match Score", f"{rec.get('score', 90)}%")

                else:
                    st.error(response.json().get("error"))
                    
            except Exception as e:
                st.error("API quota exceeded or an error occurred. Please try again later.")

# Footer
st.markdown("---")
st.caption("Built with FastAPI, Gemini 2.0, and AniList API.")