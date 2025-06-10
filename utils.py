# utils.py

import streamlit as st
import pandas as pd
import random
import os
import logging
from datetime import datetime
from config import * # Import all constants from our new config file

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False

# --- PDF INVOICE CLASS ---
class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH): self.image(LOGO_PATH, 10, 8, 33)
        self.set_font('Arial', 'B', 15); self.cell(80); self.cell(30, 10, 'Invoice', 0, 0, 'C'); self.ln(20)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- DATA LOADING ---
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

# --- HELPER FUNCTIONS ---
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

def get_bot_response(user_input: str):
    lowered_input = user_input.lower()
    customer_info = st.session_state.get('customer_info', {})
    car_details = st.session_state.get('car_in_chat', {})
    car_name = f"{car_details.get('year', '')} {car_details.get('make', '')} {car_details.get('model', '')}"
    if any(keyword in lowered_input for keyword in ["another car", "start over", "change car", "go back"]):
        st.session_state.offer_placed = False
        st.session_state.chat_messages = []; st.session_state.car_in_chat = {}
        st.rerun()
    if not customer_info.get("country"):
        return "I see we haven't confirmed your destination. To which country will you be shipping the vehicle?"
    if not customer_info.get("port_of_discharge"):
        return f"Thanks! And which port in {customer_info.get('country')} will be the port of discharge?"
    if "invoice" in lowered_input:
        return "Absolutely. I can prepare the proforma invoice. Just to confirm, are you ready to proceed with the purchase at the displayed price?"
    if any(keyword in lowered_input for keyword in ["yes", "proceed", "confirm", "i agree"]) and st.session_state.get('invoice_request_pending'):
        st.session_state.generate_invoice_request = True
        return "Excellent! Generating your invoice now. Please use the download button that appears."
    st.session_state.invoice_request_pending = "shall I issue" in lowered_input or "are you ready to proceed" in lowered_input
    if any(keyword in lowered_input for keyword in ["payment", "pay", "bank"]):
        return "We accept wire transfers to our corporate bank account in Tokyo. The full details will be on the proforma invoice."
    if any(keyword in lowered_input for keyword in ["price", "discount", "negotiate", "offer"]):
        price_breakdown = calculate_total_price(car_details.get('price', 0), st.session_state.get('shipping_option'))
        total_price = f"{int(price_breakdown['total_price']):,}"
        return f"The current total price is ¥{total_price} {st.session_state.get('shipping_option')}. Our prices are competitive, but feel free to state your best offer for our sales team to review."
    return "That's a great question. I am forwarding it to a human sales representative who will get back to you shortly, either here in the chat or via email."
