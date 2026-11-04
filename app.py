import streamlit as st

import ia

st.set_page_config(
    page_title="RMS Internal Audit Action Tracker",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ia.render_page()
