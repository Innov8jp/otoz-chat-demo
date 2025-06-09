# ======================================================
# STAGE 1: BASIC STARTUP TEST
# ======================================================
import streamlit as st

st.set_page_config(page_title="App Test - Stage 1")

st.title("✅ Application Test - Stage 1")

st.success("If you can see this message, the basic Streamlit environment is working correctly.")

st.info("Please reply with the message 'Stage 1 works' if you see this.")

# We stop the script here on purpose.
st.stop()
