import re
import random
import altair as alt
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os
import logging

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False
    logging.warning("fpdf module not found. PDF invoicing will be disabled.")

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
    try:
        if os.path.exists(INVENTORY_FILE_PATH):
            df = pd.read_csv(INVENTORY_FILE_PATH)
            # Validate required columns
            required_columns = ['make', 'model', 'year', 'price']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column '{col}' missing in inventory data")
        else:
            logging.warning(f"Inventory file not found at {INVENTORY_FILE_PATH}, using sample data")
            car_data = [
                {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000},
                {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000},
            ]
            df = pd.DataFrame(car_data * 50)

        # Add missing columns with default values
        if 'mileage' not in df.columns:
            df['mileage'] = [random.randint(*MILEAGE_RANGE) for _ in range(len(df))]
        if 'location' not in df.columns:
            df['location'] = [random.choice(DUMMY_LOCATIONS) for _ in range(len(df))]
        if 'fuel' not in df.columns:
            df['fuel'] = ['Gasoline'] * len(df)
        if 'transmission' not in df.columns:
            df['transmission'] = [random.choice(["Auto", "Manual"]) for _ in range(len(df))]
        if 'color' not in df.columns:
            df['color'] = [random.choice(['White', 'Black', 'Silver', 'Blue', 'Red']) for _ in range(len(df))]
        if 'grade' not in df.columns:
            df['grade'] = ['Standard'] * len(df)

        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
        df['id'] = [f"VID{i:04d}" for i in range(len(df))]
        return df

    except Exception as e:
        logging.error(f"Error loading inventory: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def simulate_price_history(df):
    try:
        history = []
        today = pd.to_datetime(datetime.now())
        for _, car in df.iterrows():
            base_price = car['price']
            for m in range(1, 7):
                date = today - DateOffset(months=m)
                price = base_price * (0.995 ** m) * (1 + random.uniform(-0.05, 0.05))
                history.append({
                    "make": car['make'],
                    "model": car['model'],
                    "date": date,
                    "avg_price": max(100000, int(price))  # Ensure price doesn't go below 100,000 JPY
                })
        return pd.DataFrame(history)
    except Exception as e:
        logging.error(f"Error simulating price history: {str(e)}")
        return pd.DataFrame()

def calculate_total_price(base_price, option):
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0:
            raise ValueError("Invalid base price")
            
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
    except Exception as e:
        logging.error(f"Error calculating total price: {str(e)}")
        return base_price

def display_car_card(car, shipping_option):
    try:
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(car['image_url'], use_column_width=True)
            with col2:
                st.subheader(f"{car.get('year', 'Unknown')} {car.get('make', 'Unknown')} {car.get('model', '')}")
                
                mileage = car.get('mileage', None)
                st.write(f"**Mileage:** {int(mileage):,} km" if pd.notnull(mileage) else "**Mileage:** N/A")
                
                st.write(f"**Color:** {car.get('color', 'N/A')}  |  **Transmission:** {car.get('transmission', 'N/A')}")
                st.write(f"**Location:** {car.get('location', 'N/A')}")
                st.write(f"**Base Price:** ¥{car.get('price', 0):,}")
                
                total_price = calculate_total_price(car['price'], shipping_option)
                st.success(f"**Total Price ({shipping_option}): ¥{int(total_price):,}**")
    except Exception as e:
        st.error(f"Error displaying car card: {str(e)}")

def main():
    st.set_page_config(PAGE_TITLE, PAGE_ICON, layout="wide")
    st.title(PAGE_TITLE)

    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory could not be loaded. Please try again later.")
        return

    st.markdown("## 🔍 Select Your Ideal Car")
    
    shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"], horizontal=True)
    
    car = inventory.sample(1).iloc[0]
    display_car_card(car, shipping_option)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("❤️ Place Offer", key="place_offer"):
            st.success("Offer Placed! Our team will contact you shortly.")
    with col2:
        if st.button("❌ Pass (Next Car)", key="next_car"):
            st.experimental_rerun()

if __name__ == "__main__":
    main()
