import re
import random
import altair as alt
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset

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


# --- API & Data URLs ---
DUMMY_INVENTORY_URL = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)

# --- UI Constants ---
BOT_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
USER_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/456/456212.png"

# --- Business Logic Constants (JAPAN-FOCUSED) ---
CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55} # JPY is the base currency
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
DUMMY_MAKES = ["Toyota", "Honda", "Nissan", "Suzuki", "Mazda", "Subaru", "Mitsubishi", "Lexus"]
DUMMY_MODELS = {
    "Toyota": ["Corolla", "Camry", "RAV4", "Prius", "Yaris", "Hilux", "Fortuner", "Land Cruiser"],
    "Honda": ["Civic", "Accord", "CR-V", "Fit", "Jazz", "HR-V", "Odyssey", "Pilot"],
    "Nissan": ["Sentra", "Altima", "Rogue", "Versa", "Note", "Serena"],
    "Suzuki": ["Swift", "Alto", "Vitara", "Jimny"],
    "Mazda": ["Mazda3", "Mazda6", "CX-5", "CX-30"],
    "Subaru": ["Impreza", "Outback", "Forester", "Levorg"],
    "Mitsubishi": ["Lancer", "Outlander", "Pajero", "Delica"],
    "Lexus": ["IS", "ES", "RX", "NX"],
}
MAX_DEALS_TO_SHOW = 3
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 10_000_000)


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
            "filters": {"make": "", "model": "", "year": (2018, 2024), "mileage": MILEAGE_RANGE},
            "currency": "JPY", "chat_started": False,
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)
        if "inventory_df" not in self.ss:
            self.ss.inventory_df = self._load_inventory()
            self.ss.price_history_df = self._simulate_price_history()

    @st.cache_data
    def _load_inventory(_self):
        try:
            df = pd.read_csv(DUMMY_INVENTORY_URL, on_bad_lines='skip')
            df = df.dropna(subset=['make', 'model', 'year', 'price'])
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
            df['price'] = pd.to_numeric(df['price'], errors='coerce').astype('Int64')
            if 'mileage' not in df.columns:
                 df['mileage'] = [random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]) for _ in range(len(df))]
            return df
        except Exception:
            inv = []
            for i in range(1000):
                make = random.choice(DUMMY_MAKES)
                model = random.choice(DUMMY_MODELS.get(make, ["Model"]))
                inv.append({
                    "year": random.randint(2015, 2025), "make": make, "model": model,
                    "price": random.randint(BUDGET_RANGE_JPY[0], BUDGET_RANGE_JPY[1]),
                    "location": random.choice(DUMMY_LOCATIONS),
                    "mileage": random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]),
                    "image_url": f"https://placehold.co/600x400/grey/white?text={make}+{model}",
                    "id": f"VID{i:04d}"
                })
            return pd.DataFrame(inv)

    @st.cache_data
    def _simulate_price_history(_self):
        history, inventory = [], _self._load_inventory()
        today = pd.to_datetime(datetime.now())
        for _, car in inventory.iterrows():
            base_price = car['price']
            for month_offset in range(1, 25):
                sim_date, price_fluctuation = today - DateOffset(months=month_offset), 1 + (random.random() - 0.5) * 0.05
                sim_price = base_price * (0.992 ** month_offset) * price_fluctuation
                history.append({"make": car['make'], "model": car['model'], "date": sim_date, "avg_price": int(sim_price)})
        return pd.DataFrame(history)

    def add_message(self, role, content, ui_elements=None):
        self.ss.history.append({"role": role, "content": content, "ui": ui_elements})
        if role == 'user' and self.ss.negotiation_context and self._parse_intent(content)[0] not in ['negotiate', 'accept_offer', 'reject_offer']:
            self.ss.negotiation_context = None

    def _parse_intent(self, user_input):
        text = user_input.lower()
        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "i agree", "accept", "fine"]): return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another"]): return "reject_offer", {}
        if any(w in text for w in ["invoice", "bill", "receipt"]): return "request_invoice", {}
        if text == "show deals": return "show_deals",
