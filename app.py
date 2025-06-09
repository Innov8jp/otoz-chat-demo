import re
import random
import altair as alt
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.offsets import DateOffset
import os
import logging
from typing import Optional, Dict, Any

try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False
    logging.warning("fpdf module not found. PDF invoicing will be disabled.")

# Constants
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

@st.cache_data
def load_inventory() -> pd.DataFrame:
    try:
        if os.path.exists(INVENTORY_FILE_PATH):
            df = pd.read_csv(INVENTORY_FILE_PATH)
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
            df = pd.DataFrame(car_data * 5)

        # Add missing columns with default values
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
        logging.error(f"Error loading inventory: {str(e)}")
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
                    "make": car['make'],
                    "model": car['model'],
                    "date": date,
                    "avg_price": max(100000, int(price))
                })
        return pd.DataFrame(history)
    except Exception as e:
        logging.error(f"Error simulating price history: {str(e)}")
        return pd.DataFrame()

def calculate_total_price(base_price: float, option: str) -> float:
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0:
            raise ValueError("Invalid base price")
            
        if option == "FOB":
            return base_price + DOMESTIC_TRANSPORT
        elif option == "C&F":
            return base_price + DOMESTIC_TRANSPORT + FREIGHT_COST
        elif option == "CIF":
            insurance = INSURANCE_RATE * base_price
            return base_price + DOMESTIC_TRANSPORT + FREIGHT_COST + insurance
        return base_price
    except Exception as e:
        logging.error(f"Error calculating total price: {str(e)}")
        return base_price

def generate_pdf_invoice(car: Dict[str, Any], customer_info: Dict[str, str], shipping_option: str) -> Optional[str]:
    if not ENABLE_PDF_INVOICING:
        return None

    try:
        total_price = calculate_total_price(car['price'], shipping_option)
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Seller Info
        pdf.cell(0, 10, f"Seller: {SELLER_INFO['name']}", 0, 1)
        pdf.cell(0, 10, f"Address: {SELLER_INFO['address']}", 0, 1)
        pdf.cell(0, 10, f"Phone: {SELLER_INFO['phone']}", 0, 1)
        pdf.ln(10)
        
        # Customer Info
        pdf.cell(0, 10, f"Customer: {customer_info.get('name', '')}", 0, 1)
        pdf.cell(0, 10, f"Email: {customer_info.get('email', '')}", 0, 1)
        pdf.cell(0, 10, f"Phone: {customer_info.get('phone', '')}", 0, 1)
        pdf.ln(10)
        
        # Vehicle Info
        pdf.cell(0, 10, "Vehicle Details:", 0, 1)
        pdf.cell(0, 10, f"{car['year']} {car['make']} {car['model']}", 0, 1)
        pdf.cell(0, 10, f"VIN: {car.get('id', 'N/A')}", 0, 1)
        pdf.cell(0, 10, f"Color: {car.get('color', 'N/A')}", 0, 1)
        pdf.ln(10)
        
        # Pricing
        pdf.cell(0, 10, f"Base Price: ¥{car['price']:,}", 0, 1)
        pdf.cell(0, 10, f"Shipping Option: {shipping_option}", 0, 1)
        
        if shipping_option != "Ex-Works":
            pdf.cell(0, 10, f"Domestic Transport: ¥{DOMESTIC_TRANSPORT:,}", 0, 1)
            if shipping_option in ["C&F", "CIF"]:
                pdf.cell(0, 10, f"Freight Cost: ¥{FREIGHT_COST:,}", 0, 1)
            if shipping_option == "CIF":
                insurance = INSURANCE_RATE * car['price']
                pdf.cell(0, 10, f"Insurance: ¥{insurance:,.0f}", 0, 1)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Total Price: ¥{total_price:,.0f}", 0, 1)
        
        # Save the PDF
        if not os.path.exists("invoices"):
            os.makedirs("invoices")
            
        filename = f"invoices/invoice_{car['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf.output(filename)
        return filename
    except Exception as e:
        logging.error(f"Error generating PDF invoice: {str(e)}")
        return None

def display_market_data_chart(df: pd.DataFrame, make: str, model: str):
    try:
        if df.empty:
            return
            
        filtered = df[(df['make'] == make) & (df['model'] == model)]
        if filtered.empty:
            return
            
        chart = alt.Chart(filtered).mark_line().encode(
            x='date:T',
            y='avg_price:Q',
            tooltip=['date', 'avg_price']
        ).properties(
            title=f"Price Trend for {make} {model}",
            width=600,
            height=300
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception as e:
        logging.error(f"Error displaying market data chart: {str(e)}")

def user_info_form() -> Dict[str, str]:
    with st.sidebar:
        st.header("Customer Information")
        with st.form("customer_info"):
            name = st.text_input("Full Name", key="cust_name")
            email = st.text_input("Email", key="cust_email")
            phone = st.text_input("Phone Number", key="cust_phone")
            address = st.text_area("Shipping Address", key="cust_address")
            
            submitted = st.form_submit_button("Save Information")
            if submitted:
                return {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "address": address
                }
    return {}

def car_filters(inventory: pd.DataFrame) -> Dict[str, Any]:
    with st.sidebar:
        st.header("Filters")
        
        makes = sorted(inventory['make'].unique())
        selected_make = st.selectbox("Make", ["All"] + makes)
        
        models = []
        if selected_make != "All":
            models = sorted(inventory[inventory['make'] == selected_make]['model'].unique())
            selected_model = st.selectbox("Model", ["All"] + models)
        else:
            selected_model = "All"
        
        year_range = (int(inventory['year'].min()), int(inventory['year'].max()))
        selected_years = st.slider(
            "Year Range",
            min_value=year_range[0],
            max_value=year_range[1],
            value=year_range
        )
        
        price_range = (int(inventory['price'].min()), int(inventory['price'].max()))
        selected_prices = st.slider(
            "Price Range (JPY)",
            min_value=price_range[0],
            max_value=price_range[1],
            value=price_range
        )
        
        transmission = st.multiselect(
            "Transmission",
            options=sorted(inventory['transmission'].unique()),
            default=sorted(inventory['transmission'].unique())
        )
        
        colors = st.multiselect(
            "Colors",
            options=sorted(inventory['color'].unique()),
            default=sorted(inventory['color'].unique())
        )
        
        return {
            "make": selected_make,
            "model": selected_model,
            "year_min": selected_years[0],
            "year_max": selected_years[1],
            "price_min": selected_prices[0],
            "price_max": selected_prices[1],
            "transmission": transmission,
            "colors": colors
        }

def filter_inventory(inventory: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    filtered = inventory.copy()
    
    if filters['make'] != "All":
        filtered = filtered[filtered['make'] == filters['make']]
        if filters['model'] != "All":
            filtered = filtered[filtered['model'] == filters['model']]
    
    filtered = filtered[
        (filtered['year'] >= filters['year_min']) &
        (filtered['year'] <= filters['year_max']) &
        (filtered['price'] >= filters['price_min']) &
        (filtered['price'] <= filters['price_max']) &
        (filtered['transmission'].isin(filters['transmission'])) &
        (filtered['color'].isin(filters['colors']))
    ]
    
    return filtered

def display_car_card(car: Dict[str, Any], shipping_option: str):
    try:
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(car['image_url'], use_column_width=True)
            with col2:
                st.subheader(f"{car.get('year', 'Unknown')} {car.get('make', 'Unknown')} {car.get('model', '')}")
                
                st.write(f"**ID:** {car.get('id', 'N/A')}")
                st.write(f"**Location:** {car.get('location', 'N/A')}")
                
                mileage = car.get('mileage', None)
                st.write(f"**Mileage:** {int(mileage):,} km" if pd.notnull(mileage) else "**Mileage:** N/A")
                
                st.write(f"**Color:** {car.get('color', 'N/A')}  |  **Transmission:** {car.get('transmission', 'N/A')}")
                st.write(f"**Fuel:** {car.get('fuel', 'N/A')}  |  **Grade:** {car.get('grade', 'N/A')}")
                st.write(f"**Base Price:** ¥{car.get('price', 0):,}")
                
                total_price = calculate_total_price(car['price'], shipping_option)
                st.success(f"**Total Price ({shipping_option}): ¥{int(total_price):,}**")
                
                # Display price breakdown on expander
                with st.expander("Price Breakdown"):
                    st.write(f"- Base Price: ¥{car['price']:,}")
                    if shipping_option != "Ex-Works":
                        st.write(f"- Domestic Transport: ¥{DOMESTIC_TRANSPORT:,}")
                        if shipping_option in ["C&F", "CIF"]:
                            st.write(f"- Freight Cost: ¥{FREIGHT_COST:,}")
                        if shipping_option == "CIF":
                            insurance = INSURANCE_RATE * car['price']
                            st.write(f"- Insurance ({INSURANCE_RATE*100}%): ¥{insurance:,.0f}")
                    st.write(f"**Total: ¥{total_price:,.0f}**")
    except Exception as e:
        st.error(f"Error displaying car card: {str(e)}")

def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title(PAGE_TITLE)
    st.markdown("---")
    
    # Initialize session state
    if 'current_car_index' not in st.session_state:
        st.session_state.current_car_index = 0
    
    # Load data
    inventory = load_inventory()
    if inventory.empty:
        st.error("Inventory could not be loaded. Please try again later.")
        return
    
    price_history = simulate_price_history(inventory)
    
    # Get user info
    customer_info = user_info_form()
    
    # Apply filters
    filters = car_filters(inventory)
    filtered_inventory = filter_inventory(inventory, filters)
    
    if filtered_inventory.empty:
        st.warning("No vehicles match your filters. Please adjust your criteria.")
        return
    
    # Ensure current car index is within bounds
    if st.session_state.current_car_index >= len(filtered_inventory):
        st.session_state.current_car_index = 0
    
    # Get current car
    current_car = filtered_inventory.iloc[st.session_state.current_car_index]
    
    # Main content
    st.markdown("## 🔍 Vehicle Details")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        shipping_option = st.radio(
            "Shipping Option",
            ["FOB", "C&F", "CIF"],
            horizontal=True,
            key="shipping_option"
        )
    
    display_car_card(current_car, shipping_option)
    
    # Display market data chart
    display_market_data_chart(price_history, current_car['make'], current_car['model'])
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("❤️ Place Offer", key="place_offer", use_container_width=True):
            if not all(customer_info.values()):
                st.error("Please complete your customer information first")
            else:
                st.success("Offer Placed! Our team will contact you shortly.")
                if ENABLE_PDF_INVOICING:
                    pdf_path = generate_pdf_invoice(current_car, customer_info, shipping_option)
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="Download Invoice",
                                data=f,
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf"
                            )
    
    with col2:
        if st.button("❌ Next Vehicle", key="next_car", use_container_width=True):
            st.session_state.current_car_index += 1
            if st.session_state.current_car_index >= len(filtered_inventory):
                st.session_state.current_car_index = 0
            st.rerun()
    
    st.markdown("---")
    st.markdown(f"*Showing vehicle {st.session_state.current_car_index + 1} of {len(filtered_inventory)}*")

if __name__ == "__main__":
    main()
