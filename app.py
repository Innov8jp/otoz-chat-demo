# ======================================================
# STAGE 2: LIBRARY IMPORT TEST
# ======================================================
import streamlit as st
import traceback

st.set_page_config(page_title="App Test - Stage 2")

st.title("✅ Application Test - Stage 1 Passed")
st.write("---")
st.header("Running Stage 2: Testing Library Imports...")


# We will now try to import all the necessary libraries.
# If this fails, the error will be caught and displayed on the screen.
try:
    import pandas as pd
    import altair as alt
    from fpdf import FPDF
    import re
    import random
    from datetime import datetime
    from pandas.tseries.offsets import DateOffset
    import os
    import logging

    st.success("All libraries imported successfully!")
    st.info("Please reply with the message 'Stage 2 works' if you see this.")

except Exception as e:
    st.error("A critical error occurred while importing a library.")
    st.error(f"This means there is likely a problem with your requirements.txt file or the version of a specific library.")
    st.error(f"Error Type: {type(e).__name__}")
    st.error(f"Error Details: {e}")
    st.code(traceback.format_exc())


# We stop the script here on purpose.
st.stop()
