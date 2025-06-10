# ==============================================================================
# FINAL PRODUCTION SCRIPT (v3 - Enhanced Chatbot)
# ==============================================================================

# --- SECTION 1: IMPORTS ---
import streamlit as st
import traceback
import re
import random
import altair as alt
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os
import logging

# --- SECTION 2: GLOBAL CONSTANTS & CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False
    logging.warning("fpdf2 module not found. PDF invoicing will be disabled.")

BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
PAGE_ICON = "🚗"
SELLER_INFO = {
    "name": "Otoz.ai", "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678", "email": "sales@otoz.ai"
}
LOGO_PATH = "otoz_logo.png"
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'
MILEAGE_RANGE = (5_000, 150_000)
DOMESTIC_TRANSPORT = 50_000
FREIGHT_COST = 150_000
INSURANCE_RATE = 0.025

CAR_MAKERS_AND_MODELS = {
    "Toyota": ["Aqua", "Vitz", "Passo", "Corolla", "Prius", "Harrier", "RAV4", "Land Cruiser", "HiAce"],
    "Honda": ["Fit", "Vezel", "CR-V", "Civic", "Accord", "N-BOX", "Freed"],
    "Nissan": ["Note", "Serena", "X-Trail", "Leaf", "Skyline", "March", "Juke"],
    "Mazda": ["Demio", "CX-5", "CX-8", "Mazda3", "Mazda6", "Roadster"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "GLC", "A-Class"],
    "BMW": ["3 Series", "5 Series", "X1", "X3", "X5", "1 Series"]
}
CAR_COLORS = ['White', 'Black', 'Silver', 'Gray', 'Blue', 'Red', 'Beige', 'Brown', 'Green', 'Pearl White', 'Dark Blue', 'Maroon']
PORTS_BY_COUNTRY = {
    "Australia": ["Adelaide", "Brisbane", "Fremantle", "Melbourne", "Sydney"], "Canada": ["Halifax", "Vancouver"],
    "Chile": ["Iquique", "Valparaíso"], "Germany": ["Bremerhaven", "Hamburg"], "Ireland": ["Cork", "Dublin"],
    "Kenya": ["Mombasa"], "Malaysia": ["Port Klang"], "New Zealand": ["Auckland", "Lyttelton", "Napier", "Wellington"],
    "Pakistan": ["Karachi", "Port Qasim"], "Tanzania": ["Dar es Salaam"], "Thailand": ["Laem Chabang"],
    "United Arab Emirates": ["Jebel Ali (Dubai)"], "United Kingdom": ["Bristol", "Liverpool", "Southampton", "Tilbury"],
    "United States": ["Baltimore", "Jacksonville", "Long Beach", "Newark", "Tacoma"], "Zambia": ["(Via Dar es Salaam, Tanzania)"]
}

# --- SECTION 3: PDF INVOICE CLASS ---
class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH): self.image(LOGO_PATH, 10, 8, 33)
        self.set_font('Arial', 'B', 15); self.cell(80); self.cell(30, 10, 'Invoice', 0, 0, 'C'); self.ln(20)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- SECTION 4: DATA LOADING ---
@st.cache_data
def load_inventory():
    try:
        df = None
        if os.path.exists(INVENTORY_FILE_PATH):
            try:
                df_from_file = pd.read_csv(INVENTORY_FILE_PATH)
                if not df_from_file.empty:
                    required_columns = ['make', 'model', 'year', 'price']
                    if all(col in df_from_file.columns for col in required_columns):
                        df = df_from_file
                    else: logging.warning("CSV is missing required columns. Generating sample data.")
                else: logging.warning("Inventory CSV file is empty. Generating sample data.")
            except Exception as read_error:
                logging.error(f"Could not read CSV file: {read_error}. Generating sample data.")
        if df is None:
            car_data = []
            current_year = datetime.now().year
            for make, models in CAR_MAKERS_AND_MODELS.items():
                for model in models:
                    for _ in range(random.randint(2, 3)):
                        year = random.randint(current_year - 8, current_year - 1)
                        base_price_factor = 3_000_000 if make in ["Mercedes-Benz", "BMW"] else 1_500_000
                        price = int(base_price_factor * (0.85 ** (current_year - year)) * random.uniform(0.9, 1.1))
                        car_data.append({'make': make, 'model': model, 'year': year, 'price': max(300_000, price)})
            df = pd.DataFrame(car_data)
        defaults = {
            'mileage': lambda: random.randint(*MILEAGE_RANGE), 'location': lambda: random.choice(list(PORTS_BY_COUNTRY.keys())),
            'fuel': 'Gasoline', 'transmission': lambda: random.choice(["Automatic", "Manual"]),
            'color': lambda: random.choice(CAR_COLORS), 'grade': lambda: random.choice(["4.5", "4.0", "3.5", "R"])
        }
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = [default() if callable(default) else default for _ in range(len(df))]
        df.reset_index(drop=True, inplace=True)
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
        df['id'] = [f"VID{i:04d}" for i in df.index]
        return df
    except Exception as e:
        logging.error(f"FATAL: Error during inventory loading: {e}"); st.error(f"A fatal error occurred while preparing inventory data: {e}"); return pd.DataFrame()

# --- SECTION 5: HELPER FUNCTIONS ---
def calculate_total_price(base_price, option):
    breakdown = {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0}
    if option in ["FOB", "C&F", "CIF"]: breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
    if option in ["C&F", "CIF"]: breakdown['freight_cost'] = FREIGHT_COST
    if option == "CIF":
        cost_and_freight = base_price + breakdown['freight_cost']
        breakdown['insurance'] = cost_and_freight * INSURANCE_RATE
    breakdown['total_price'] = sum(breakdown.values())
    return breakdown

def generate_pdf_invoice(car, customer_info, shipping_option):
    if not ENABLE_PDF_INVOICING: return None
    try:
        price_breakdown = calculate_total_price(car['price'], shipping_option)
        pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
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

### NEW BOT BRAIN ###
def get_bot_response(user_input: str) -> str:
    """Generates a rule-based response from the bot based on keywords."""
    lowered_input = user_input.lower()
    car_details = st.session_state.get('car_in_chat', {})
    car_name = f"{car_details.get('year', '')} {car_details.get('make', '')} {car_details.get('model', '')}"

    if any(keyword in lowered_input for keyword in ["payment", "pay", "bank", "invoice", "finance"]):
        return "We accept wire transfers to our corporate bank account in Tokyo. The full details will be on the proforma invoice we send you."
    if any(keyword in lowered_input for keyword in ["shipping", "delivery", "port", "freight", "ship"]):
        port = st.session_state.customer_info.get('port_of_discharge', 'your selected port')
        country = st.session_state.customer_info.get('country', 'your country')
        return f"We handle all export procedures from Japan. The C&F and CIF prices include all costs to get the vehicle to {port}, {country}. Do you have a specific question about the timeline?"
    if any(keyword in lowered_input for keyword in ["discount", "negotiate", "price", "offer", "best"]):
        return "Our prices are set based on market conditions and auction data. For the best offer on this vehicle, please state your proposed price, and our sales team will review it promptly."
    if any(keyword in lowered_input for keyword in ["hello", "hi", "hey"]):
        return f"Hello there! I'm Sparky. I'm here to help with your offer on the {car_name}. What would you like to know?"
    
    return "That's a great question. I am forwarding it to a human sales representative who will get back to you shortly, either here in the chat or via email."


# --- SECTION 6: UI FUNCTIONS ---
def user_info_form():
    with st.sidebar:
        st.header("Your Information")
        with st.form("customer_info_form"):
            name = st.text_input("Full Name", st.session_state.customer_info.get("name", ""))
            email = st.text_input("Email", st.session_state.customer_info.get("email", ""))
            phone = st.text_input("Phone Number", st.session_state.customer_info.get("phone", ""))
            countries = sorted(list(PORTS_BY_COUNTRY.keys()))
            selected_country = st.selectbox("Country", countries, index=None, placeholder="Select your country...")
            available_ports = PORTS_BY_COUNTRY.get(selected_country, [])
            selected_port = st.selectbox("Port of Discharge", available_ports, index=None, placeholder="Select a port...", disabled=not selected_country)
            if st.form_submit_button("Save Details"):
                st.session_state.customer_info = {"name": name, "email": email, "phone": phone, "country": selected_country, "port_of_discharge": selected_port}
                st.success("Your details have been saved!")

def car_filters(inventory):
    with st.sidebar:
        st.header("Vehicle Filters")
        if inventory.empty:
            st.warning("No inventory data found to apply filters."); return
        with st.form("car_filters_form"):
            make_list = ["All"] + sorted(inventory['make'].unique())
            selected_make = st.selectbox("Make", make_list, index=0)
            model_list = ["All"]
            if selected_make != "All": model_list += sorted(inventory[inventory['make'] == selected_make]['model'].unique())
            selected_model = st.selectbox("Model", model_list, index=0)
            year_min, year_max = int(inventory['year'].min()), int(inventory['year'].max())
            selected_years = st.slider("Year", year_min, year_max, (year_min, year_max))
            price_min, price_max = 0, int(inventory['price'].max())
            selected_prices = st.slider("Price (JPY)", price_min, price_max, (price_min, price_max), step=50000)
            if st.form_submit_button("Show Results"):
                st.session_state.active_filters = {"make": selected_make, "model": selected_model, "year_min": selected_years[0], "year_max": selected_years[1], "price_min": selected_prices[0], "price_max": selected_prices[1]}
                st.session_state.current_car_index = 0; st.rerun()

def filter_inventory(inventory, filters):
    if not filters: return inventory
    query = "(year >= @filters['year_min']) & (year <= @filters['year_max']) & (price >= @filters['price_min']) & (price <= @filters['price_max'])"
    if filters['make'] != "All":
        query += " & (make == @filters['make'])"
        if filters['model'] != "All": query += " & (model == @filters['model'])"
    return inventory.query(query)

def display_car_card(car, shipping_option):
    price_breakdown = calculate_total_price(car['price'], shipping_option)
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1: st.image(car['image_url'], use_column_width=True)
        with col2:
            st.subheader(f"{car.get('year')} {car.get('make')} {car.get('model')}")
            st.write(f"**ID:** {car.get('id')} | **Mileage:** {car.get('mileage', 0):,} km")
            st.write(f"**Color:** {car.get('color')} | **Transmission:** {car.get('transmission')}")
            st.write(f"**Base Price (Vehicle Only):** ¥{car.get('price', 0):,}")
            st.success(f"**Total Price ({shipping_option}): ¥{int(price_breakdown['total_price']):,}**")
            with st.expander("Click to see full price breakdown"):
                st.markdown(f"**Base Vehicle Price:** `¥{price_breakdown['base_price']:,}`")
                if price_breakdown['domestic_transport'] > 0: st.markdown(f"**Domestic Transport (to Port):** `¥{price_breakdown['domestic_transport']:,}`")
                if price_breakdown['freight_cost'] > 0: st.markdown(f"**Ocean Freight:** `¥{price_breakdown['freight_cost']:,}`")
                if price_breakdown['insurance'] > 0: st.markdown(f"**Marine Insurance:** `¥{price_breakdown['insurance']:,.0f}`")
                st.divider(); st.markdown(f"### **Total:** `¥{price_breakdown['total_price']:,.0f}`")

### MODIFIED CHAT UI ###
def display_chat_interface():
    """Displays a simulated chat window that uses the new bot logic."""
    st.subheader("💬 Chat with our Sales Team")
    for msg in st.session_state.chat_messages:
        st.chat_message(msg["role"]).write(msg["content"])
    
    if prompt := st.chat_input("Ask about payment, shipping, or your offer..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        bot_response = get_bot_response(prompt)
        st.session_state.chat_messages.append({"role": "assistant", "content": bot_response})
        st.chat_message("assistant").write(bot_response)

# --- SECTION 7: MAIN APPLICATION ---
def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")

    # Initialize session state
    if 'current_car_index' not in st.session_state: st.session_state.current_car_index = 0
    if 'customer_info' not in st.session_state: st.session_state.customer_info = {}
    if 'active_filters' not in st.session_state: st.session_state.active_filters = {}
    if 'offer_placed' not in st.session_state: st.session_state.offer_placed = False
    if 'chat_messages' not in st.session_state: st.session_state.chat_messages = []
    if 'car_in_chat' not in st.session_state: st.session_state.car_in_chat = {}

    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    
    inventory = load_inventory()
    if inventory.empty:
        st.error("Critical Error: Inventory data could not be loaded. Application cannot continue."); return
    
    user_info_form()
    car_filters(inventory)
    
    if st.session_state.offer_placed:
        display_chat_interface(); return

    filtered_inventory = filter_inventory(inventory, st.session_state.active_filters)
    if filtered_inventory.empty:
        st.warning("No vehicles match your current filters. Please adjust your criteria and click 'Show Results'."); return

    if st.session_state.current_car_index >= len(filtered_inventory): st.session_state.current_car_index = 0
    current_car = filtered_inventory.iloc[st.session_state.current_car_index]
    
    st.markdown("---")
    st.markdown(f"#### Showing Vehicle {st.session_state.current_car_index + 1} of {len(filtered_inventory)}")
    shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"], horizontal=True, key="shipping_option")
    display_car_card(current_car, shipping_option)

    col1, col2, _ = st.columns([1.5, 1.5, 4])
    with col1:
        if st.button("❤️ Place Offer", use_container_width=True):
            if not all(st.session_state.customer_info.get(key) for key in ["name", "email", "phone", "country", "port_of_discharge"]):
                st.error("Please complete all fields in 'Your Information' and click 'Save Details' first.")
            else:
                st.session_state.offer_placed = True
                st.session_state.car_in_chat = current_car.to_dict() # Save car context for the bot

                if not st.session_state.chat_messages:
                    st.session_state.chat_messages = [{"role": "assistant", "content": f"Hello {st.session_state.customer_info['name']}! Thank you for your interest in the {current_car['year']} {current_car['make']} {current_car['model']}. How can I help you?"}]
                st.rerun()
    with col2:
        if st.button("❌ Next Vehicle", use_container_width=True):
            st.session_state.current_car_index = (st.session_state.current_car_index + 1) % len(filtered_inventory)
            st.rerun()

# --- SECTION 8: SCRIPT ENTRY POINT ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("A critical error occurred. Please contact support.")
        st.code(traceback.format_exc())
