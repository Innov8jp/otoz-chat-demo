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
            "filters": {"make": "", "model": "", "year": (2018, 2024), "mileage": MILEAGE_RANGE, "fuel": "", "transmission": "", "color": "", "grade": ""},
            "currency": "JPY", "chat_started": False,
            "query_context": {}, "search_results": [], "search_results_index": 0
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)
        if "inventory_df" not in self.ss:
            inventory = self._load_inventory()
            self.ss.inventory_df = inventory
            self.ss.price_history_df = self._simulate_price_history(inventory)

    @st.cache_data
    def _load_inventory(_self):
        # Using a high-quality internal dataset for 100% reliability and a professional demo.
        car_data = [
            {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Silver', 'grade': '4.5'},
            {'make': 'Toyota', 'model': 'Prius', 'year': 2019, 'price': 1200000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'White', 'grade': 'S'},
            {'make': 'Toyota', 'model': 'Vitz', 'year': 2017, 'price': 750000, 'fuel': 'Petrol', 'transmission': 'Automatic', 'color': 'Black', 'grade': '4'},
            {'make': 'Honda', 'model': 'Fit', 'year': 2018, 'price': 800000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Blue', 'grade': '4'},
            {'make': 'Honda', 'model': 'Vezel', 'year': 2019, 'price': 1500000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Red', 'grade': '4.5'},
            {'make': 'Nissan', 'model': 'Note', 'year': 2020, 'price': 950000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'White', 'grade': 'S'},
            {'make': 'Nissan', 'model': 'Serena', 'year': 2018, 'price': 1300000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Silver', 'grade': '4'},
            {'make': 'Mazda', 'model': 'Demio', 'year': 2017, 'price': 700000, 'fuel': 'Diesel', 'transmission': 'Automatic', 'color': 'Grey', 'grade': '3.5'},
            {'make': 'Mazda', 'model': 'CX-5', 'year': 2019, 'price': 1800000, 'fuel': 'Diesel', 'transmission': 'Automatic', 'color': 'Black', 'grade': '4.5'},
            {'make': 'Suzuki', 'model': 'Swift', 'year': 2021, 'price': 1100000, 'fuel': 'Petrol', 'transmission': 'Automatic', 'color': 'Orange', 'grade': '5'},
            {'make': 'Isuzu', 'model': 'Elf', 'year': 2016, 'price': 2500000, 'fuel': 'Diesel', 'transmission': 'Manual', 'color': 'White', 'grade': 'R'},
            {'make': 'Mitsubishi', 'model': 'Canter', 'year': 2017, 'price': 2800000, 'fuel': 'Diesel', 'transmission': 'Manual', 'color': 'Blue', 'grade': '3.5'},
        ]
        
        df = pd.DataFrame(car_data * 50) # Multiply to create a larger dataset
        df['location'] = [random.choice(DUMMY_LOCATIONS) for _ in range(len(df))]
        df['mileage'] = [random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]) for _ in range(len(df))]
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make.replace(' ','+')}+{r.model.replace(' ','+')}" for r in df.itertuples()]
        df.reset_index(drop=True, inplace=True)
        df['id'] = [f"VID{i:04d}" for i in df.index]
        return df

    @st.cache_data
    def _simulate_price_history(_self, inventory_df):
        history = []
        today = pd.to_datetime(datetime.now())
        for _, car in inventory_df.iterrows():
            base_price = car['price']
            for month_offset in range(1, 13):
                sim_date, price_fluctuation = today - DateOffset(months=month_offset), 1 + (random.random() - 0.5) * 0.05
                sim_price = base_price * (0.992 ** month_offset) * price_fluctuation
                history.append({"make": car['make'], "model": car['model'], "date": sim_date, "avg_price": int(sim_price)})
        return pd.DataFrame(history)

    def add_message(self, role, content, ui_elements=None):
        self.ss.history.append({"role": role, "content": content, "ui": ui_elements})
    
    def _parse_intent(self, user_input):
        text = user_input.lower().strip()
        
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if text in greeting_words:
            return "greeting", {}

        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "i agree", "accept", "fine"]): return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another", "cancel"]): return "reject_offer", {}
            if any(w in text for w in ["discount", "best price", "negotiate"]): return "discount_inquiry", {}
            if any(w in text for w in ["what", "why", "don't understand"]): return "clarification_request", {}
        if any(w in text for w in ["invoice", "bill", "receipt"]): return "request_invoice", {}
        if text == "show deals": return "show_deals", {}
        if text == "next car" or text == "next": return "show_next_deal", {}
        if text == "contact support": return "contact_support", {}
        
        all_known_makes = list(self.ss.inventory_df['make'].unique())
        
        makes_pattern = r'\b(' + '|'.join(re.escape(m.lower()) + r's?' for m in all_known_makes) + r')\b'
        make_match = re.search(makes_pattern, text)
        make = None
        if make_match:
            make_str = make_match.group(1)
            if make_str.endswith
