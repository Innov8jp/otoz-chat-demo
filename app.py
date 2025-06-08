import re
import random
import altair as alt
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os

# fpdf is an optional dependency for invoice generation.
# The app will run without it, but the invoice feature will be disabled.
try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False

# ======================================================================================
# 1. Configuration & Constants
# ======================================================================================

# --- App Configuration ---
BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
PAGE_ICON = "🚗"
SELLER_INFO = {
    "name": "Otoz.ai",
    "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678",
    "email": "sales@otoz.ai"
}


# --- UI Constants ---
BOT_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
USER_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/456/456212.png"

# --- Business Logic Constants (JAPAN-FOCUSED) ---
CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55} # JPY is the base currency
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
MAX_DEALS_TO_SHOW = 1 # Show one at a time to guide the user
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 15_000_000)


# ======================================================================================
# 2. Agentic Core Logic (SalesAgent Class)
# ======================================================================================

class SalesAgent:
    def __init__(self, session_state):
        self.ss = session_state
        self._initialize_state()

    def _initialize_state(self):
        defaults = {
            "history": [], "negotiation_context": None, "last_deal_context": None,
            "user_profile": {"name": "", "email": "", "country": "", "budget": (1_500_000, 5_000_000)},
            "filters": {"make": "", "model": "", "y
