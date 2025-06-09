import re
import random
import altair as alt
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False

BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
PAGE_ICON = "🚗"
SELLER_INFO = {
    "name": "Otoz.ai",
    "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678",
    "email": "sales@otoz.ai"
}

LOGO_PATH = "otoz_logo.png"
MARKET_DATA_FILE_PATH = 'market_prices.csv'
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'

CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55}
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 15_000_000)
PROGRESS_STEPS = ["Purchase", "Payment", "In Land Transportation", "Inspection", "Shipping", "On Shore", "Receiving"]

@st.cache_data
def load_inventory():
    if os.path.exists(INVENTORY_FILE_PATH):
        df = pd.read_csv(INVENTORY_FILE_PATH)
    else:
        car_data = [
            {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000},
            {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000},
        ]
        df = pd.DataFrame(car_data * 50)

    for col in ['mileage', 'location', 'fuel', 'transmission', 'color', 'grade']:
        if col not in df.columns:
            df[col] = [random.choice(DUMMY_LOCATIONS if col == 'location' else ["Auto", "Manual"] if col == 'transmission' else ['White', 'Black']) for _ in range(len(df))]

    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce').fillna(100000).astype(int)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(1000000).astype(int)
    df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
    df['id'] = [f"VID{i:04d}" for i in range(len(df))]
    return df

@st.cache_data
def simulate_price_history(df):
    history = []
    today = pd.to_datetime(datetime.now())
    for _, car in df.iterrows():
        base_price = car['price']
        for m in range(1, 7):
            date = today - DateOffset(months=m)
            price = base_price * (0.995 ** m) * (1 + random.uniform(-0.05, 0.05))
            history.append({"make": car['make'], "model": car['model'], "date": date, "avg_price": int(price)})
    return pd.DataFrame(history)

def calculate_total_price(base_price, option):
    domestic = 100
    freight = 1500
    if option == "FOB":
        return base_price + domestic
    elif option == "C&F":
        return base_price + domestic + freight
    elif option == "CIF":
        insurance = 0.02 * base_price
        return base_price + domestic + freight + insurance
    return base_price

def main():
    st.set_page_config(PAGE_TITLE, PAGE_ICON, layout="wide")
    st.title(PAGE_TITLE)

    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory could not be loaded.")
        return

    if 'chat_stage' not in st.session_state:
        st.session_state.chat_stage = 0
        st.session_state.user_query = {}

    user_input = st.chat_input("Ask Sparky about cars...")

    if user_input:
        if st.session_state.chat_stage == 0:
            st.chat_message("assistant").write("Hello! I’m Sparky. What make are you interested in? (e.g., Toyota, Honda)")
            st.session_state.chat_stage = 1
        elif st.session_state.chat_stage == 1:
            st.session_state.user_query['make'] = user_input.title()
            st.chat_message("assistant").write("Got it. Any specific color you're looking for?")
            st.session_state.chat_stage = 2
        elif st.session_state.chat_stage == 2:
            st.session_state.user_query['color'] = user_input.title()
            st.chat_message("assistant").write("Noted. What’s your maximum mileage preference?")
            st.session_state.chat_stage = 3
        elif st.session_state.chat_stage == 3:
            try:
                mileage = int(user_input.replace(',', ''))
            except:
                mileage = 100000
            st.session_state.user_query['mileage'] = mileage
            st.chat_message("assistant").write("Great! What's your budget in JPY?")
            st.session_state.chat_stage = 4
        elif st.session_state.chat_stage == 4:
            try:
                budget = int(user_input.replace(',', ''))
            except:
                budget = 3000000
            st.session_state.user_query['budget'] = budget
            query = st.session_state.user_query
            df = inventory[(inventory['make'].str.lower() == query['make'].lower()) &
                           (inventory['color'].str.lower() == query['color'].lower()) &
                           (inventory['mileage'] <= int(query['mileage'])) &
                           (inventory['price'] <= int(query['budget']))]
            if df.empty:
                st.chat_message("assistant").write("Sorry, I couldn't find a match. Try adjusting your preferences.")
            else:
                car = df.sample(1).iloc[0]
                st.chat_message("assistant").write(f"Here's a great match: {car['year']} {car['make']} {car['model']} ({car['color']}) at {car['price']:,} JPY")
                st.image(car['image_url'], use_container_width=True)
            st.session_state.chat_stage = 0
            st.session_state.user_query = {}

if __name__ == "__main__":
    main()

# --- End of script ---
