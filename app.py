# app.py

import streamlit as st
import traceback
import pandas as pd
from config import *
from utils import *

# --- UI FUNCTIONS (These functions control the layout of the app) ---
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
            st.warning("No inventory data found."); return
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

def display_chat_interface():
    st.subheader("💬 Chat with our Sales Team")
    for msg in st.session_state.chat_messages:
        st.chat_message(msg["role"]).write(msg["content"])
    if st.session_state.get('generate_invoice_request'):
        pdf_path = generate_pdf_invoice(st.session_state.car_in_chat, st.session_state.customer_info, st.session_state.shipping_option)
        if pdf_path:
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download Proforma Invoice", f, file_name=os.path.basename(pdf_path), mime="application/pdf")
        st.session_state.generate_invoice_request = False
    if prompt := st.chat_input("Ask a question or type 'start over'..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        bot_response = get_bot_response(prompt)
        st.session_state.chat_messages.append({"role": "assistant", "content": bot_response})
        st.rerun()

# --- MAIN APPLICATION ---
def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")

    # Initialize session state
    state_keys = {
        'current_car_index': 0, 'customer_info': {}, 'active_filters': {},
        'offer_placed': False, 'chat_messages': [], 'car_in_chat': {},
        'generate_invoice_request': False, 'invoice_request_pending': False
    }
    for key, default_value in state_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    
    inventory = load_inventory()
    if inventory.empty:
        st.error("Critical Error: Inventory data could not be loaded."); return
    
    user_info_form()
    car_filters(inventory)
    
    if st.session_state.active_filters:
        active_filter_str = " | ".join([f"{k.split('_')[0].title()}: {v}" for k,v in st.session_state.active_filters.items() if v != 'All' and not isinstance(v, (int, float))])
        st.info(f"**Active Filters:** {active_filter_str if active_filter_str else 'Showing all vehicles.'}")

    filtered_inventory = filter_inventory(inventory, st.session_state.active_filters)
    if filtered_inventory.empty:
        st.warning("No vehicles match your current filters. Please adjust your criteria and click 'Show Results'."); return

    if st.session_state.current_car_index >= len(filtered_inventory): st.session_state.current_car_index = 0
    
    if st.session_state.offer_placed:
        st.markdown("---")
        st.markdown(f"### Continuing your offer for:")
        display_car_card(pd.Series(st.session_state.car_in_chat), st.session_state.shipping_option)
        display_chat_interface()
    else:
        current_car = filtered_inventory.iloc[st.session_state.current_car_index]
        st.markdown("---")
        st.markdown(f"#### Showing Vehicle {st.session_state.current_car_index + 1} of {len(filtered_inventory)}")
        shipping_option = st.radio("Shipping Option", ["FOB", "C&F", "CIF"], horizontal=True, key="shipping_option_main")
        display_car_card(current_car, shipping_option)

        col1, col2, _ = st.columns([1.5, 1.5, 4])
        with col1:
            if st.button("❤️ Place Offer", use_container_width=True):
                if not all(st.session_state.customer_info.get(key) for key in ["name", "email", "phone", "country", "port_of_discharge"]):
                    st.error("Please complete all fields in 'Your Information' and click 'Save Details' first.")
                else:
                    st.session_state.offer_placed = True
                    st.session_state.car_in_chat = current_car.to_dict()
                    st.session_state.shipping_option = shipping_option
                    if not st.session_state.chat_messages:
                        st.session_state.chat_messages = [{"role": "assistant", "content": f"Hello {st.session_state.customer_info['name']}! I'm Sparky. I can help you finalize your offer on the {current_car['year']} {current_car['make']} {current_car['model']}. What would you like to know?"}]
                    st.rerun()
        with col2:
            if st.button("❌ Next Vehicle", use_container_width=True):
                st.session_state.current_car_index = (st.session_state.current_car_index + 1) % len(filtered_inventory)
                st.rerun()

# --- SCRIPT ENTRY POINT ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("A critical error occurred. Please contact support.")
        st.code(traceback.format_exc())
