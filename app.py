# ==============================================================================
# SECTION 1: IMPORTS
# ==============================================================================

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

# ==============================================================================
# SECTION 2: GLOBAL CONSTANTS & CONFIGURATION
# ==============================================================================

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Feature Flag for PDF Invoicing ---
try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False
    logging.warning("fpdf module not found. PDF invoicing will be disabled.")

# --- Application Constants ---
BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
PAGE_ICON = "🚗"

# --- Business Information ---
SELLER_INFO = {
    "name": "Otoz.ai", "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678", "email": "sales@otoz.ai"
}

# --- File Paths and Data Parameters ---
LOGO_PATH = "otoz_logo.png"
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'
MILEAGE_RANGE = (5_000, 150_000)

# --- Shipping Cost Parameters (in JPY) ---
DOMESTIC_TRANSPORT = 50_000
FREIGHT_COST = 150_000
INSURANCE_RATE = 0.025  # 2.5%

### NEW: Curated list of Countries and their major Ports for the dependent dropdown ###
PORTS_BY_COUNTRY = {
    "Australia": ["Adelaide", "Brisbane", "Fremantle", "Melbourne", "Sydney"],
    "Canada": ["Halifax", "Vancouver"],
    "Chile": ["Iquique", "Valparaíso"],
    "Germany": ["Bremerhaven", "Hamburg"],
    "Ireland": ["Cork", "Dublin"],
    "Kenya": ["Mombasa"],
    "Malaysia": ["Port Klang"],
    "New Zealand": ["Auckland", "Lyttelton", "Napier", "Wellington"],
    "Pakistan": ["Karachi", "Port Qasim"],
    "Tanzania": ["Dar es Salaam"],
    "Thailand": ["Laem Chabang"],
    "United Arab Emirates": ["Jebel Ali (Dubai)"],
    "United Kingdom": ["Bristol", "Liverpool", "Southampton", "Tilbury"],
    "United States": ["Baltimore", "Jacksonville", "Long Beach", "Newark", "Tacoma"],
    "Zambia": ["(Via Dar es Salaam, Tanzania)"]
}


# ==============================================================================
# SECTION 3: PDF INVOICE CLASS DEFINITION
# ==============================================================================

class PDF(FPDF):
    """Custom PDF class to define a standard header and footer for invoices."""
    def header(self):
        if os.path.exists(LOGO_PATH): self.image(LOGO_PATH, 10, 8, 33)
        self.set_font('Arial', 'B', 15); self.cell(80); self.cell(30, 10, 'Invoice', 0, 0, 'C'); self.ln(20)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# ==============================================================================
# SECTION 4: DATA LOADING & SIMULATION FUNCTIONS
# ==============================================================================

@st.cache_data
def load_inventory() -> pd.DataFrame:
    """Loads inventory from a CSV file or creates a sample DataFrame if not found."""
    # (This function remains unchanged)
    try:
        if os.path.exists(INVENTORY_FILE_PATH):
            df = pd.read_csv(INVENTORY_FILE_PATH)
            required_columns = ['make', 'model', 'year', 'price']
            if not all(col in df.columns for col in required_columns):
                 raise ValueError(f"Inventory CSV must contain: {', '.join(required_columns)}")
        else:
            logging.warning(f"Inventory file not found at {INVENTORY_FILE_PATH}, using sample data.")
            car_data = [{'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000}, {'make': 'Honda', 'model': 'Fit', 'year': 2019, 'price': 1200000}]
            df = pd.DataFrame(car_data * 5)
        defaults = {
            'mileage': lambda: random.randint(*MILEAGE_RANGE), 'location': lambda: random.choice(list(PORTS_BY_COUNTRY.keys())),
            'fuel': 'Gasoline', 'transmission': lambda: random.choice(["Auto", "Manual"]),
            'color': lambda: random.choice(['White', 'Black', 'Silver', 'Blue', 'Red']), 'grade': 'Standard'
        }
        for col, default in defaults.items():
            if col not in df.columns: df[col] = [default() if callable(default) else default for _ in range(len(df))]
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
        df['id'] = [f"VID{i:04d}" for i in range(len(df))]
        return df
    except Exception as e:
        logging.error(f"Error loading inventory: {e}"); return pd.DataFrame()

# ==============================================================================
# SECTION 5: CORE LOGIC & HELPER FUNCTIONS
# ==============================================================================

### CHANGED: Corrected Price Calculation Logic ###
def calculate_total_price(base_price: float, option: str) -> Dict[str, float]:
    """
    Calculate total price with a full breakdown.
    CIF Insurance is now calculated based on the C&F value.
    """
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0: raise ValueError("Invalid base price")
        breakdown = {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0}
        
        # FOB includes domestic transport to the port
        if option in ["FOB", "C&F", "CIF"]:
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
            
        # C&F includes ocean freight
        if option in ["C&F", "CIF"]:
            breakdown['freight_cost'] = FREIGHT_COST
            
        # CIF includes insurance on top of C&F value
        if option == "CIF":
            # Standard formula: Insurance on (Cost + Freight) value
            cost_and_freight = base_price + breakdown['freight_cost']
            breakdown['insurance'] = cost_and_freight * INSURANCE_RATE
            
        breakdown['total_price'] = sum(breakdown.values())
        return breakdown
    except Exception as e:
        logging.error(f"Error calculating total price: {e}")
        return {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0, 'total_price': base_price}

def generate_pdf_invoice(car: pd.Series, customer_info: Dict[str, str], shipping_option: str) -> Optional[str]:
    """Generates a PDF invoice. Now uses the same price breakdown as the UI."""
    # (This function is updated to use the new price breakdown logic)
    if not ENABLE_PDF_INVOICING: return None
    try:
        price_breakdown = calculate_total_price(car['price'], shipping_option)
        pdf = PDF()
        pdf.add_page(); pdf.set_font("Arial", size=12)
        for key, value in SELLER_INFO.items(): pdf.cell(0, 7, f"Seller {key.capitalize()}: {value}", 0, 1)
        pdf.ln(10)
        for key, value in customer_info.items():
             if key not in ['country', 'port_of_discharge']: pdf.cell(0, 7, f"Customer {key.capitalize()}: {value}", 0, 1)
        if customer_info.get("country"): pdf.cell(0, 7, f"Destination: {customer_info.get('port_of_discharge', 'N/A')}, {customer_info.get('country')}", 0, 1)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "Vehicle Details", 0, 1); pdf.set_font("Arial", size=12)
        pdf.cell(0, 7, f"{car['year']} {car['make']} {car['model']} (ID: {car.get('id', 'N/A')})", 0, 1)
        pdf.cell(0, 7, f"Color: {car.get('color', 'N/A')}, Transmission: {car.get('transmission', 'N/A')}", 0, 1); pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"Pricing ({shipping_option})", 0, 1); pdf.set_font("Arial", size=12)
        for key, value in price_breakdown.items():
            if value > 0 and key != 'total_price': pdf.cell(0, 7, f"- {key.replace('_', ' ').capitalize()}: ¥{value:,.0f}", 0, 1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, f"Total Price: ¥{price_breakdown['total_price']:,.0f}", 0, 1)
        if not os.path.exists("invoices"): os.makedirs("invoices")
        filename = f"invoices/invoice_{car['id']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(filename)
        return filename
    except Exception as e:
        logging.error(f"Error generating PDF invoice: {e}"); return None

# ==============================================================================
# SECTION 6: UI COMPONENT FUNCTIONS
# ==============================================================================

### CHANGED: User form now includes a dependent dropdown for Ports ###
def user_info_form():
    """Displays the customer information form in the sidebar and saves data to session state."""
    with st.sidebar:
        st.header("Your Information")
        with st.form("customer_info_form"):
            name = st.text_input("Full Name", st.session_state.customer_info.get("name", ""))
            email = st.text_input("Email", st.session_state.customer_info.get("email", ""))
            phone = st.text_input("Phone Number", st.session_state.customer_info.get("phone", ""))
            
            countries = list(PORTS_BY_COUNTRY.keys())
            selected_country = st.selectbox("Country", countries, index=None, placeholder="Select your country...")
            
            available_ports = PORTS_BY_COUNTRY.get(selected_country, [])
            selected_port = st.selectbox("Port of Discharge", available_ports, index=None, placeholder="Select a port...", disabled=not selected_country)

            if st.form_submit_button("Save Details"):
                st.session_state.customer_info = {
                    "name": name, "email": email, "phone": phone,
                    "country": selected_country, "port_of_discharge": selected_port,
                }
                st.success("Your details have been saved!")

### CHANGED: Car filters are now in a form with a submit button ###
def car_filters(inventory: pd.DataFrame):
    """Displays vehicle filter widgets in a form and stores selection in session_state upon submission."""
    with st.sidebar:
        st.header("Vehicle Filters")
        with st.form("car_filters_form"):
            make_list = ["All"] + sorted(inventory['make'].unique())
            selected_make = st.selectbox("Make", make_list, index=0)
            
            model_list = ["All"]
            if selected_make != "All":
                model_list += sorted(inventory[inventory['make'] == selected_make]['model'].unique())
            selected_model = st.selectbox("Model", model_list, index=0)

            year_min, year_max = int(inventory['year'].min()), int(inventory['year'].max())
            selected_years = st.slider("Year", year_min, year_max, (year_min, year_max))
            
            price_min, price_max = 0, int(inventory['price'].max())
            selected_prices = st.slider("Price (JPY)", price_min, price_max, (price_min, price_max), step=50000)

            submitted = st.form_submit_button("Show Results")
            if submitted:
                st.session_state.active_filters = {
                    "make": selected_make, "model": selected_model,
                    "year_min": selected_years[0], "year_max": selected_years[1],
                    "price_min": selected_prices[0], "price_max": selected_prices[1],
                }
                st.session_state.current_car_index = 0 # Reset index on new filter
                st.rerun()

def filter_inventory(inventory: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Filters the inventory DataFrame based on active filters."""
    if not filters: return inventory # Return all if no filters are set
    
    query = "(year >= @filters['year_min']) & (year <= @filters['year_max']) & (price >= @filters['price_min']) & (price <= @filters['price_max'])"
    if filters['make'] != "All":
        query += " & (make == @filters['make'])"
        if filters['model'] != "All": query += " & (model == @filters['model'])"
    return inventory.query(query)

### CHANGED: Price breakdown display is now more explicit ###
def display_car_card(car: pd.Series, shipping_option: str):
    """Displays the main card with vehicle details and a clear price breakdown."""
    try:
        price_breakdown = calculate_total_price(car['price'], shipping_option)
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(car['image_url'], use_column_width=True)
            with col2:
                st.subheader(f"{car.get('year')} {car.get('make')} {car.get('model')}")
                st.write(f"**ID:** {car.get('id')} | **Mileage:** {car.get('mileage', 0):,} km")
                st.write(f"**Color:** {car.get('color')} | **Transmission:** {car.get('transmission')}")
                st.write(f"**Base Price (Vehicle Only):** ¥{car.get('price', 0):,}")
                st.success(f"**Total Price ({shipping_option}): ¥{int(price_breakdown['total_price']):,}**")

                with st.expander("Click to see full price breakdown"):
                    st.markdown(f"**Base Vehicle Price:** `¥{price_breakdown['base_price']:,}`")
                    if price_breakdown['domestic_transport'] > 0:
                        st.markdown(f"**Domestic Transport (to Port):** `¥{price_breakdown['domestic_transport']:,}`")
                    if price_breakdown['freight_cost'] > 0:
                        st.markdown(f"**Ocean Freight:** `¥{price_breakdown['freight_cost']:,}`")
                    if price_breakdown['insurance'] > 0:
                        st.markdown(f"**Marine Insurance:** `¥{price_breakdown['insurance']:,.0f}`")
                    st.divider()
                    st.markdown(f"### **Total:** `¥{price_breakdown['total_price']:,.0f}`")
    except Exception as e:
        st.error(f"Error displaying car card: {e}")

### NEW: Chat Interface Function ###
def display_chat_interface():
    """Displays a simulated chat window for post-offer interaction."""
    st.subheader("💬 Chat with our Sales Team")
    for msg in st.session_state.chat_messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Your message..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        # Add a simple auto-reply from the bot
        st.session_state.chat_messages.append({"role": "assistant", "content": "Thank you for your message. A sales representative will be with you shortly."})
        st.chat_message("assistant").write("Thank you for your message. A sales representative will be with you shortly.")
        st.rerun()

# ==============================================================================
# SECTION 7: MAIN APPLICATION
# ==============================================================================

def main():
    """The main function that orchestrates the Streamlit application."""
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")

    # Initialize session state variables
    if 'current_car_index' not in st.session_state: st.session_state.current_car_index = 0
    if 'customer_info' not in st.session_state: st.session_state.customer_info = {}
    if 'active_filters' not in st.session_state: st.session_state.active_filters = {}
    if 'offer_placed' not in st.session_state: st.session_state.offer_placed = False

    # Load data and manage sidebar
    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory data could not be loaded."); return
    user_info_form()
    car_filters(inventory) # This will update st.session_state.active_filters
    
    # Check if an offer has been placed to decide the view
    if st.session_state.offer_placed:
        display_chat_interface()
        return # End execution here to only show the chat

    # --- Main Vehicle Display ---
    filtered_inventory = filter_inventory(inventory, st.session_state.active_filters)
    if filtered_inventory.empty:
        st.warning("No vehicles match your current filters. Please adjust your criteria and click 'Show Results'."); return

    current_car = filtered_inventory.iloc[st.session_state.current_car_index]
    st.markdown("---")
    st.markdown(f"#### Showing Vehicle {st.session_state.current_car_index + 1} of {len(filtered_inventory)}")
    shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"], horizontal=True, key="shipping_option")
    display_car_card(current_car, shipping_option)

    # --- Action Buttons ---
    col1, col2, _ = st.columns([1.5, 1.5, 4])
    with col1:
        if st.button("❤️ Place Offer", use_container_width=True):
            if not all(st.session_state.customer_info.get(key) for key in ["name", "email", "phone", "country", "port_of_discharge"]):
                st.error("Please complete all fields in 'Your Information' (including Country/Port) and click 'Save Details' first.")
            else:
                st.session_state.offer_placed = True
                st.session_state.chat_messages = [{"role": "assistant", "content": f"Hello {st.session_state.customer_info['name']}! Thank you for your interest in the {current_car['year']} {current_car['make']} {current_car['model']}. How can I help you finalize your offer?"}]
                st.rerun()
    with col2:
        if st.button("❌ Next Vehicle", use_container_width=True):
            st.session_state.current_car_index = (st.session_state.current_car_index + 1) % len(filtered_inventory)
            st.rerun()

# ==============================================================================
# SECTION 8: SCRIPT ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
