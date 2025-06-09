Of course. Here is the fully revised and improved version of your Streamlit application.

The new `calculate_total_price` and `display_car_card` functions have been integrated, and several performance and logic enhancements have been made throughout the code. I've also fixed a few minor bugs.

### Key Improvements

* **Duplicate Imports Removed:** Cleaned up redundant `import streamlit as st`.
* **Refactored Price Calculation:** The `calculate_total_price` function now returns a dictionary with a full price breakdown, and this is gracefully used in both the `display_car_card` and `generate_pdf_invoice` functions. This centralizes the logic and avoids recalculating prices.
* **Stateful Customer Info:** The `user_info_form` now uses `st.session_state` to store customer information, so it isn't lost on every rerun or button click.
* **Bug Fix:** The `generate_pdf_invoice` function was trying to access `customer_info` that was not being passed to it. This has been corrected.
* **Code Cleanup:** A stray line of code (`if st.button(...)`) at the end of the script has been removed to prevent errors.
* **Error Handling:** Enhanced the `try...except` blocks with more specific logging for better debugging.

***

### Revised Code

```python
import streamlit as st
import re
import random
import altair as alt
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os
import logging
from typing import Optional, Dict, Any

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False
    logging.warning("fpdf module not found. PDF invoicing will be disabled.")

# --- Constants ---
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
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'

CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55}
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
MILEAGE_RANGE = (5_000, 150_000)
PROGRESS_STEPS = ["Purchase", "Payment", "In Land Transportation", "Inspection", "Shipping", "On Shore", "Receiving"]

# Shipping cost parameters (in JPY)
DOMESTIC_TRANSPORT = 50_000
FREIGHT_COST = 150_000
INSURANCE_RATE = 0.02  # 2% of base price

# --- PDF Class for Invoicing ---
class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Invoice', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- Data Loading and Simulation ---
@st.cache_data
def load_inventory() -> pd.DataFrame:
    try:
        if os.path.exists(INVENTORY_FILE_PATH):
            df = pd.read_csv(INVENTORY_FILE_PATH)
            required_columns = ['make', 'model', 'year', 'price']
            if not all(col in df.columns for col in required_columns):
                 raise ValueError(f"Inventory CSV must contain: {', '.join(required_columns)}")
        else:
            logging.warning(f"Inventory file not found at {INVENTORY_FILE_PATH}, using sample data")
            car_data = [
                {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000},
                {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000},
            ]
            df = pd.DataFrame(car_data * 5)

        defaults = {
            'mileage': lambda: random.randint(*MILEAGE_RANGE),
            'location': lambda: random.choice(DUMMY_LOCATIONS),
            'fuel': 'Gasoline',
            'transmission': lambda: random.choice(["Auto", "Manual"]),
            'color': lambda: random.choice(['White', 'Black', 'Silver', 'Blue', 'Red']),
            'grade': 'Standard'
        }

        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = [default() if callable(default) else default for _ in range(len(df))]

        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
        df['id'] = [f"VID{i:04d}" for i in range(len(df))]
        return df

    except Exception as e:
        logging.error(f"Error loading inventory: {e}")
        return pd.DataFrame()

@st.cache_data
def simulate_price_history(df: pd.DataFrame) -> pd.DataFrame:
    try:
        history = []
        today = pd.to_datetime(datetime.now())
        for _, car in df.iterrows():
            base_price = car['price']
            for m in range(1, 7):
                date = today - DateOffset(months=m)
                price = base_price * (0.995 ** m) * (1 + random.uniform(-0.05, 0.05))
                history.append({
                    "make": car['make'], "model": car['model'],
                    "date": date, "avg_price": max(100000, int(price))
                })
        return pd.DataFrame(history)
    except Exception as e:
        logging.error(f"Error simulating price history: {e}")
        return pd.DataFrame()

# --- Core Logic Functions ---
def calculate_total_price(base_price: float, option: str) -> Dict[str, float]:
    """Calculate total price with a full breakdown of components."""
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0:
            raise ValueError("Invalid base price")
            
        breakdown = {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0}
        
        if option in ["FOB", "C&F", "CIF"]:
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
        if option in ["C&F", "CIF"]:
            breakdown['freight_cost'] = FREIGHT_COST
        if option == "CIF":
            breakdown['insurance'] = INSURANCE_RATE * base_price
            
        breakdown['total_price'] = sum(breakdown.values())
        return breakdown

    except Exception as e:
        logging.error(f"Error calculating total price: {e}")
        return {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0, 'total_price': base_price}

def generate_pdf_invoice(car: pd.Series, customer_info: Dict[str, str], shipping_option: str) -> Optional[str]:
    if not ENABLE_PDF_INVOICING:
        return None
    try:
        price_breakdown = calculate_total_price(car['price'], shipping_option)
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Seller & Customer Info
        for key, value in SELLER_INFO.items():
            pdf.cell(0, 7, f"Seller {key.capitalize()}: {value}", 0, 1)
        pdf.ln(10)
        for key, value in customer_info.items():
            pdf.cell(0, 7, f"Customer {key.capitalize()}: {value}", 0, 1)
        pdf.ln(10)
        
        # Vehicle Details
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Vehicle Details", 0, 1)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 7, f"{car['year']} {car['make']} {car['model']} (ID: {car.get('id', 'N/A')})", 0, 1)
        pdf.cell(0, 7, f"Color: {car.get('color', 'N/A')}, Transmission: {car.get('transmission', 'N/A')}", 0, 1)
        pdf.ln(10)

        # Pricing
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Pricing ({shipping_option})", 0, 1)
        pdf.set_font("Arial", size=12)
        for key, value in price_breakdown.items():
            if value > 0 and key != 'total_price':
                label = key.replace('_', ' ').capitalize()
                pdf.cell(0, 7, f"- {label}: ¥{value:,.0f}", 0, 1)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Total Price: ¥{price_breakdown['total_price']:,.0f}", 0, 1)
        
        if not os.path.exists("invoices"):
            os.makedirs("invoices")
        filename = f"invoices/invoice_{car['id']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(filename)
        return filename
    except Exception as e:
        logging.error(f"Error generating PDF invoice: {e}")
        return None

# --- UI Component Functions ---
def user_info_form():
    with st.sidebar:
        st.header("Customer Information")
        with st.form("customer_info_form"):
            st.session_state.customer_info = {
                "name": st.text_input("Full Name", st.session_state.get("customer_info", {}).get("name", "")),
                "email": st.text_input("Email", st.session_state.get("customer_info", {}).get("email", "")),
                "phone": st.text_input("Phone Number", st.session_state.get("customer_info", {}).get("phone", "")),
                "address": st.text_area("Shipping Address", st.session_state.get("customer_info", {}).get("address", "")),
            }
            if st.form_submit_button("Save Information"):
                st.success("Information saved!")

def car_filters(inventory: pd.DataFrame) -> Dict[str, Any]:
    with st.sidebar:
        st.header("Vehicle Filters")
        makes = ["All"] + sorted(inventory['make'].unique())
        selected_make = st.selectbox("Make", makes)
        
        models = ["All"]
        if selected_make != "All":
            models += sorted(inventory[inventory['make'] == selected_make]['model'].unique())
        selected_model = st.selectbox("Model", models)

        year_min, year_max = int(inventory['year'].min()), int(inventory['year'].max())
        selected_years = st.slider("Year", year_min, year_max, (year_min, year_max))
        
        price_min, price_max = int(inventory['price'].min()), int(inventory['price'].max())
        selected_prices = st.slider("Price (JPY)", price_min, price_max, (price_min, price_max), step=50000)

        return {
            "make": selected_make, "model": selected_model,
            "year_min": selected_years[0], "year_max": selected_years[1],
            "price_min": selected_prices[0], "price_max": selected_prices[1],
        }

def filter_inventory(inventory: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    query = "(year >= @filters['year_min']) & (year <= @filters['year_max']) & (price >= @filters['price_min']) & (price <= @filters['price_max'])"
    if filters['make'] != "All":
        query += " & (make == @filters['make'])"
        if filters['model'] != "All":
            query += " & (model == @filters['model'])"
    return inventory.query(query)

def display_car_card(car: pd.Series, shipping_option: str):
    try:
        price_breakdown = calculate_total_price(car['price'], shipping_option)
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(car['image_url'], use_column_width=True)
            with col2:
                st.subheader(f"{car.get('year', 'Unknown')} {car.get('make', 'Unknown')} {car.get('model', '')}")
                st.write(f"**ID:** {car.get('id', 'N/A')} | **Location:** {car.get('location', 'N/A')}")
                mileage = car.get('mileage', 0)
                st.write(f"**Mileage:** {mileage:,} km")
                st.write(f"**Color:** {car.get('color', 'N/A')} | **Transmission:** {car.get('transmission', 'N/A')}")
                st.write(f"**Base Price:** ¥{car.get('price', 0):,}")
                st.success(f"**Total Price ({shipping_option}): ¥{int(price_breakdown['total_price']):,}**")

                with st.expander("See Price Breakdown"):
                    for key, value in price_breakdown.items():
                        if value > 0 and key != 'total_price':
                             label = key.replace('_', ' ').capitalize()
                             st.write(f"- {label}: ¥{int(value):,}")
                    st.write(f"**Total: ¥{int(price_breakdown['total_price']):,}**")
    except Exception as e:
        st.error(f"Error displaying car card: {e}")

def display_market_data_chart(df: pd.DataFrame, make: str, model: str):
    filtered_data = df.query("make == @make and model == @model")
    if filtered_data.empty: return
    try:
        chart = alt.Chart(filtered_data).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('avg_price:Q', title='Average Price (JPY)'),
            tooltip=['date:T', 'avg_price:Q']
        ).properties(title=f"6-Month Price Trend for {make} {model}")
        st.altair_chart(chart, use_container_width=True)
    except Exception as e:
        logging.error(f"Error displaying market chart: {e}")

# --- Main Application ---
def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    st.title(PAGE_TITLE)

    # Initialize session state
    if 'current_car_index' not in st.session_state:
        st.session_state.current_car_index = 0
    if 'customer_info' not in st.session_state:
        st.session_state.customer_info = {}

    # Load data
    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory data could not be loaded. Please check the source file.")
        return
        
    price_history = simulate_price_history(inventory)

    # Sidebar
    user_info_form()
    filters = car_filters(inventory)
    filtered_inventory = filter_inventory(inventory, filters)

    # Main content display
    if filtered_inventory.empty:
        st.warning("No vehicles match your current filters. Please adjust your criteria.")
        return

    # Handle index reset if filters change
    if st.session_state.current_car_index >= len(filtered_inventory):
        st.session_state.current_car_index = 0

    current_car = filtered_inventory.iloc[st.session_state.current_car_index]
    
    st.markdown("---")
    st.markdown(f"#### Showing Vehicle {st.session_state.current_car_index + 1} of {len(filtered_inventory)}")
    
    shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"], horizontal=True, key="shipping_option")
    display_car_card(current_car, shipping_option)

    # Action buttons
    col1, col2, col_spacer = st.columns([1.5, 1.5, 4])
    with col1:
        if st.button("❤️ Place Offer", use_container_width=True):
            if not all(st.session_state.customer_info.get(key) for key in ["name", "email", "phone"]):
                st.error("Please complete your name, email, and phone in the sidebar first.")
            else:
                st.success("Offer Placed! Our team will contact you shortly.")
                st.balloons()
                pdf_path = generate_pdf_invoice(current_car, st.session_state.customer_info, shipping_option)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download Invoice", f, file_name=os.path.basename(pdf_path), mime="application/pdf")

    with col2:
        if st.button("❌ Next Vehicle", use_container_width=True):
            st.session_state.current_car_index = (st.session_state.current_car_index + 1) % len(filtered_inventory)
            st.rerun()
            
    # Additional charts and data
    st.markdown("---")
    st.markdown("#### Market Insights")
    display_market_data_chart(price_history, current_car['make'], current_car['model'])

if __name__ == "__main__":
    main()
```
