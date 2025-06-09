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

### NEW: Enriched Vehicle Maker and Model Database ###
CAR_MAKERS_AND_MODELS = {
    "Toyota": ["Aqua", "Vitz", "Passo", "Corolla", "Prius", "Harrier", "RAV4", "Land Cruiser", "HiAce"],
    "Honda": ["Fit", "Vezel", "CR-V", "Civic", "Accord", "N-BOX", "Freed"],
    "Nissan": ["Note", "Serena", "X-Trail", "Leaf", "Skyline", "March", "Juke"],
    "Mazda": ["Demio", "CX-5", "CX-8", "Mazda3", "Mazda6", "Roadster"],
    "Subaru": ["Impreza", "Forester", "Legacy", "Levorg", "XV"],
    "Suzuki": ["Swift", "Jimny", "Hustler", "Solio", "Spacia"],
    "Daihatsu": ["Tanto", "Move", "Mira", "Rocky", "Thor"],
    "Mitsubishi": ["Outlander", "Delica", "Pajero", "eK Cross"],
    "Lexus": ["RX", "NX", "IS", "LS", "UX"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "GLC", "A-Class"],
    "BMW": ["3 Series", "5 Series", "X1", "X3", "X5", "1 Series"],
    "Audi": ["A3", "A4", "Q3", "Q5", "A1"],
    "Volkswagen": ["Golf", "Polo", "Tiguan", "Passat"],
    "Volvo": ["XC40", "XC60", "V60"],
    "Ford": ["Focus", "Fiesta", "Mustang", "Explorer"],
    "Chevrolet": ["Cruze", "Malibu", "Equinox"],
    "Hyundai": ["Tucson", "Santa Fe", "Elantra", "Kona"],
    "Kia": ["Sportage", "Sorento", "Forte", "Soul"],
    "Porsche": ["Cayenne", "Macan", "911"],
    "Land Rover": ["Range Rover Evoque", "Discovery Sport"]
}

### NEW: Expanded list of Car Colors ###
CAR_COLORS = ['White', 'Black', 'Silver', 'Gray', 'Blue', 'Red', 'Beige', 'Brown', 'Green', 'Pearl White', 'Dark Blue', 'Maroon']

# --- Port Information by Country ---
PORTS_BY_COUNTRY = {
    "Australia": ["Adelaide", "Brisbane", "Fremantle", "Melbourne", "Sydney"], "Canada": ["Halifax", "Vancouver"],
    "Chile": ["Iquique", "Valparaíso"], "Germany": ["Bremerhaven", "Hamburg"], "Ireland": ["Cork", "Dublin"],
    "Kenya": ["Mombasa"], "Malaysia": ["Port Klang"], "New Zealand": ["Auckland", "Lyttelton", "Napier", "Wellington"],
    "Pakistan": ["Karachi", "Port Qasim"], "Tanzania": ["Dar es Salaam"], "Thailand": ["Laem Chabang"],
    "United Arab Emirates": ["Jebel Ali (Dubai)"], "United Kingdom": ["Bristol", "Liverpool", "Southampton", "Tilbury"],
    "United States": ["Baltimore", "Jacksonville", "Long Beach", "Newark", "Tacoma"], "Zambia": ["(Via Dar es Salaam, Tanzania)"]
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

### CHANGED: This function now generates a rich and varied sample inventory ###
@st.cache_data
def load_inventory() -> pd.DataFrame:
    """Loads inventory from CSV, or generates a large, realistic sample DataFrame."""
    try:
        if os.path.exists(INVENTORY_FILE_PATH):
            df = pd.read_csv(INVENTORY_FILE_PATH)
            required_columns = ['make', 'model', 'year', 'price']
            if not all(col in df.columns for col in required_columns):
                 raise ValueError(f"Inventory CSV must contain: {', '.join(required_columns)}")
        else:
            logging.warning(f"Inventory file not found at {INVENTORY_FILE_PATH}. Generating a rich sample inventory.")
            car_data = []
            current_year = datetime.now().year
            # Iterate through the new database to create sample cars
            for make, models in CAR_MAKERS_AND_MODELS.items():
                for model in models:
                    # Create 2-3 sample cars for each model
                    for _ in range(random.randint(2, 3)):
                        year = random.randint(current_year - 8, current_year - 1)
                        # Simulate price based on brand and age
                        base_price_factor = 3_000_000 if make in ["Lexus", "Mercedes-Benz", "BMW", "Porsche", "Land Rover"] else 1_500_000
                        price = int(base_price_factor * (0.85 ** (current_year - year)) * random.uniform(0.9, 1.1))
                        car_data.append({'make': make, 'model': model, 'year': year, 'price': max(300_000, price)})
            
            if not car_data: raise ValueError("Sample car data could not be generated.")
            df = pd.DataFrame(car_data)

        # Define default values for optional columns
        defaults = {
            'mileage': lambda: random.randint(*MILEAGE_RANGE),
            'location': lambda: random.choice(list(PORTS_BY_COUNTRY.keys())),
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
        logging.error(f"Error loading inventory: {e}"); return pd.DataFrame()

# ==============================================================================
# SECTIONS 5 through 8 (No changes from previous version)
# ... (The rest of your code for calculations, UI, and the main app logic
# remains the same. You can paste it below this line.)
# ==============================================================================

# --- The rest of your code from the previous version goes here ---
# (I've omitted it for brevity, but you should include all functions from
# calculate_total_price down to the end of the script.)
# --- PASTE THE REST OF YOUR CODE HERE ---

def calculate_total_price(base_price: float, option: str) -> Dict[str, float]:
    """
    Calculate total price with a full breakdown.
    CIF Insurance is now calculated based on the C&F value.
    """
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0: raise ValueError("Invalid base price")
        breakdown = {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0}
        if option in ["FOB", "C&F", "CIF"]: breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
        if option in ["C&F", "CIF"]: breakdown['freight_cost'] = FREIGHT_COST
        if option == "CIF":
            cost_and_freight = base_price + breakdown['freight_cost']
            breakdown['insurance'] = cost_and_freight * INSURANCE_RATE
        breakdown['total_price'] = sum(breakdown.values())
        return breakdown
    except Exception as e:
        logging.error(f"Error calculating total price: {e}")
        return {'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0, 'total_price': base_price}

def generate_pdf_invoice(car: pd.Series, customer_info: Dict[str, str], shipping_option: str) -> Optional[str]:
    """Generates a PDF invoice. Now uses the same price breakdown as the UI."""
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

def user_info_form():
    """Displays the customer information form in the sidebar and saves data to session state."""
    with st.sidebar:
        st.header("Your Information")
        with st.form("customer_info_form"):
            name = st.text_input("Full Name", st.session_state.customer_info.get("name", ""))
            email = st.text_input("Email", st.session_state.customer_info.get("email", ""))
            phone = st.text_input("Phone Number", st.session_state.customer_info.get("phone", ""))
