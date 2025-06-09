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

MARKET_DATA_FILE_PATH = 'market_prices.csv'
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'

CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55}
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 15_000_000)
PROGRESS_STEPS = ["Purchase", "Payment", "In Land Transportation", "Inspection", "Shipping", "On Shore", "Receiving"]

COUNTRY_PORTS = {
    "Japan": ["Tokyo", "Yokohama", "Osaka", "Nagoya", "Kobe", "Fukuoka"],
    "Kenya": ["Mombasa"],
    "Tanzania": ["Dar es Salaam"],
    "Nigeria": ["Lagos", "Port Harcourt"],
    "South Africa": ["Durban", "Cape Town", "Port Elizabeth"],
    "India": ["Mumbai", "Chennai", "Kolkata", "Visakhapatnam"],
    "Pakistan": ["Karachi", "Port Qasim"],
    "Bangladesh": ["Chittagong", "Mongla"],
    "Sri Lanka": ["Colombo", "Hambantota"],
    "Indonesia": ["Jakarta", "Surabaya"],
    "Philippines": ["Manila", "Cebu"],
    "Vietnam": ["Ho Chi Minh City", "Hai Phong"],
    "Thailand": ["Laem Chabang", "Bangkok"],
    "Brazil": ["Santos", "Rio de Janeiro", "Salvador"],
    "Argentina": ["Buenos Aires", "Rosario"],
    "Colombia": ["Cartagena", "Barranquilla"],
    "Peru": ["Callao"],
    "Chile": ["Valparaíso", "San Antonio"]
}

@st.cache_data
def load_inventory():
    if os.path.exists(INVENTORY_FILE_PATH):
        try:
            df = pd.read_csv(INVENTORY_FILE_PATH)
            df.rename(columns=lambda c: c.lower().strip(), inplace=True)
            required_cols = ['make', 'model', 'year', 'price']
            if not all(col in df.columns for col in required_cols):
                st.error("Missing required columns in inventory file.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to load inventory: {e}")
            return pd.DataFrame()
    else:
        data = [
            {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000},
            {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000},
        ]
        df = pd.DataFrame(data * 50)

    for col in ['mileage', 'location', 'fuel', 'transmission', 'color', 'grade']:
        if col not in df.columns:
            df[col] = [random.choice(DUMMY_LOCATIONS if col == 'location' else ["Auto", "Manual"] if col == 'transmission' else ['White', 'Black']) for _ in range(len(df))]

    df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
    df['id'] = [f"VID{i:04d}" for i in range(len(df))]
    return df

@st.cache_data
def load_market_data():
    if os.path.exists(MARKET_DATA_FILE_PATH):
        try:
            return pd.read_csv(MARKET_DATA_FILE_PATH)
        except Exception as e:
            st.warning(f"Could not load market data: {e}")
            return None
    st.warning("Market data file not found.")
    return None

@st.cache_data
def simulate_price_history(df):
    history = []
    today = pd.to_datetime(datetime.now())
    for _, car in df.iterrows():
        base_price = car['price']
        for m in range(1, 13):
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
        insurance = 0.02 * base_price  # only on car price
        return base_price + domestic + freight + insurance
    return base_price

def render_market_comparison(agent, car):
    st.subheader("Market Price Comparison")
    market_df = agent.ss.get("market_prices_df")
    if market_df is not None:
        row = market_df[(market_df['make'] == car['make']) & (market_df['model'] == car['model']) & (market_df['year'] == car['year'])]
        if not row.empty:
            st.metric("BeForward.jp", f"{row.iloc[0]['beforward_price_jpy']:,} JPY")
            st.metric("SBTJapan.com", f"{row.iloc[0]['sbtjapan_price_jpy']:,} JPY")
    else:
        st.info("Market data unavailable.")

def main():
    st.set_page_config(PAGE_TITLE, PAGE_ICON)
    st.title(PAGE_TITLE)

    inventory = load_inventory()
    market_data = load_market_data()
    price_history = simulate_price_history(inventory)

    if inventory.empty:
        st.error("Inventory could not be loaded.")
        return

    car = inventory.sample(1).iloc[0]
    st.image(car['image_url'])
    st.markdown(f"**{car['year']} {car['make']} {car['model']}**")
    st.markdown(f"Price: {car['price']:,} JPY")

    shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"])
    total_price = calculate_total_price(car['price'], shipping_option)
    st.markdown(f"**Total Price ({shipping_option}): {int(total_price):,} JPY**")

    render_market_comparison(st.session_state, car)

if __name__ == "__main__":
    main()

# --- End of script ---
