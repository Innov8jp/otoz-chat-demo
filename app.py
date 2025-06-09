import re
import random
import altair as alt
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os

# Conditionally import FPDF for PDF generation
try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False

# --- CONSTANTS ---
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

# Define currency conversion rates relative to JPY
CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55}
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 15_000_000)
PROGRESS_STEPS = ["Purchase", "Payment", "In Land Transportation", "Inspection", "Shipping", "On Shore", "Receiving"]


@st.cache_data
def load_inventory():
    """
    Loads inventory from a CSV file or creates a dummy dataframe.
    It cleans data, fills missing values, and ensures data types are correct.
    """
    if os.path.exists(INVENTORY_FILE_PATH):
        df = pd.read_csv(INVENTORY_FILE_PATH)
    else:
        st.warning("Inventory file not found. Loading sample data.")
        car_data = [
            {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000},
            {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000},
            {'make': 'Nissan', 'model': 'Note', 'year': 2020, 'price': 1350000},
            {'make': 'Toyota', 'model': 'Vitz', 'year': 2017, 'price': 780000},
            {'make': 'Mazda', 'model': 'Demio', 'year': 2018, 'price': 950000},
        ]
        df = pd.DataFrame(car_data * 20)  # 100 cars total

    # Define generators for dummy data for potentially missing columns
    dummy_data_map = {
        'mileage': lambda: random.randint(*MILEAGE_RANGE),
        'location': lambda: random.choice(DUMMY_LOCATIONS),
        'fuel': lambda: random.choice(['Gasoline', 'Hybrid', 'Diesel']),
        'transmission': lambda: random.choice(['Automatic', 'Manual']),
        'color': lambda: random.choice(['White', 'Black', 'Silver', 'Blue', 'Red']),
        'grade': lambda: random.choice(['4.5', '4.0', '3.5', 'R'])
    }

    # Ensure all required columns exist and fill any missing values
    for col, generator in dummy_data_map.items():
        if col not in df.columns:
            df[col] = [generator() for _ in range(len(df))]
        else:
            # If column exists, fill only the missing (NaN) values
            is_na = df[col].isna()
            df.loc[is_na, col] = [generator() for _ in range(is_na.sum())]

    # Convert types for consistency and handle potential errors
    for col in ['year', 'price', 'mileage']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=[col], inplace=True) # Drop rows where essential data is missing
        df[col] = df[col].astype(int)

    # Generate a unique ID and a placeholder image URL for each car
    df.reset_index(drop=True, inplace=True)
    df['id'] = [f"VID{i:04d}" for i in df.index]
    df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
    
    return df

@st.cache_data
def simulate_price_history(df):
    """Generates a simulated 6-month price history for cars."""
    history = []
    today = pd.to_datetime(datetime.now())
    for _, car in df.iterrows():
        base_price = car['price']
        for m in range(1, 7):
            date = today - DateOffset(months=m)
            price = base_price * (0.995 ** m) * (1 + random.uniform(-0.05, 0.05))
            history.append({"make": car['make'], "model": car['model'], "date": date, "avg_price": int(price)})
    return pd.DataFrame(history)

def calculate_total_price(base_price_jpy, option):
    """
    Calculates the total price including shipping fees.
    Converts USD-based fees to JPY.
    """
    # Define costs in their original currency (USD)
    domestic_usd = 100
    freight_usd = 1500

    # Calculate the USD to JPY conversion rate from the constants
    usd_to_jpy_rate = 1 / CURRENCIES["USD"]

    # Convert USD costs to JPY
    domestic_jpy = domestic_usd * usd_to_jpy_rate
    freight_jpy = freight_usd * usd_to_jpy_rate

    # Calculate total price based on the selected shipping option
    if option == "FOB": # Free On Board
        return base_price_jpy + domestic_jpy
    elif option == "C&F": # Cost & Freight
        return base_price_jpy + domestic_jpy + freight_jpy
    elif option == "CIF": # Cost, Insurance, and Freight
        insurance_jpy = 0.02 * base_price_jpy  # 2% of base price for insurance
        return base_price_jpy + domestic_jpy + freight_jpy + insurance_jpy
    
    return base_price_jpy # Default fallback

def main():
    st.set_page_config(PAGE_TITLE, PAGE_ICON, layout="wide")
    st.title(PAGE_TITLE)

    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory data could not be loaded. Please check the data source.")
        return

    # Function to select a new car and store it in the session state
    def get_new_car():
        st.session_state.current_car = inventory.sample(1).iloc[0].to_dict()
        if 'offer_placed' in st.session_state:
            del st.session_state.offer_placed


    # --- Main App Logic ---
    # Initialize session state if it's the first run
    if 'current_car' not in st.session_state:
        get_new_car()

    st.markdown("## 🔍 Select Your Ideal Car")
    
    # Use the car stored in the session state
    car = st.session_state.current_car

    # --- Layout ---
    col1, col2 = st.columns([2, 3]) # Adjust column ratio for better layout

    with col1:
        st.image(car['image_url'], use_container_width=True)
        
        # Action buttons
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button("❤️ Place Offer", use_container_width=True):
                st.session_state.offer_placed = True
                st.rerun()
        with btn_cols[1]:
            if st.button("❌ Pass (Next Car)", use_container_width=True):
                get_new_car()
                st.rerun()

    with col2:
        st.subheader(f"{car.get('year', 'N/A')} {car.get('make', 'N/A')} {car.get('model', '')}")
        
        # Car details
        mileage = car.get('mileage', 0)
        st.write(f"**Mileage:** {mileage:,} km")
        st.write(f"**Color:** {car.get('color', 'N/A')} | **Transmission:** {car.get('transmission', 'N/A')}")
        st.write(f"**Base Price:** {car.get('price', 0):,} JPY")

        # Shipping options
        shipping_option = st.radio(
            "Shipping Option",
            ["FOB", "C&F", "CIF"],
            horizontal=True,
            # Use a unique key to prevent widget state issues on rerun
            key=f"shipping_radio_{car['id']}" 
        )
        
        total_price = calculate_total_price(car['price'], shipping_option)
        st.success(f"**Total Price ({shipping_option}): {int(total_price):,} JPY**")

    # Display a confirmation message after an offer is placed
    if st.session_state.get('offer_placed'):
        st.balloons()
        st.info(f"🎉 Offer successfully placed for the {car.get('make')} {car.get('model')}!")


if __name__ == "__main__":
    main()
