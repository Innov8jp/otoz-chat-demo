import os
import re
import csv
import io
import random
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

# fpdf is an optional dependency for invoice generation.
# The app will run without it, but the invoice feature will be disabled.
try:
    from fpdf import FPDF
    ENABLE_PDF_INVOICING = True
except ImportError:
    ENABLE_PDF_INVOICING = False

# ======================================================================================
# 1. Configuration & Constants
# ======================================================================================

# --- App Configuration ---
PAGE_TITLE = "Agentic AI Sales Assistant"
PAGE_ICON = "🚗"

# --- API & Data URLs ---
# Using a dummy CSV for inventory. In a real application, this would be a database or API.
DUMMY_INVENTORY_URL = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)

# --- UI Constants ---
BOT_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
USER_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/456/456212.png"

# --- Business Logic Constants ---
CURRENCIES = {"PKR": 1, "USD": 1/280, "JPY": 1/2.0}
DUMMY_MAKES = ["Toyota", "Honda", "Nissan", "Suzuki", "Mazda", "Subaru", "Mitsubishi", "Lexus"]
DUMMY_MODELS = {
    "Toyota": ["Corolla", "Camry", "RAV4", "Prius", "Yaris", "Hilux", "Fortuner", "Land Cruiser"],
    "Honda": ["Civic", "Accord", "CR-V", "Fit", "Jazz", "HR-V", "Odyssey", "Pilot"],
    "Nissan": ["Sentra", "Altima", "Rogue", "Versa"],
    "Suzuki": ["Swift", "Alto", "Vitara"],
    "Mazda": ["Mazda3", "Mazda6", "CX-5"],
    "Subaru": ["Impreza", "Outback", "Forester"],
    "Mitsubishi": ["Lancer", "Outlander", "Pajero"],
    "Lexus": ["IS", "ES", "RX"],
}
MAX_DEALS_TO_SHOW = 3
NEGOTIATION_MIN_DISCOUNT = 0.05  # 5%
NEGOTIATION_MAX_DISCOUNT = 0.12  # 12%

# ======================================================================================
# 2. Agentic Core Logic (SalesAgent Class)
# This class encapsulates the "brains" of the chatbot, aligning with our architecture.
# ======================================================================================

class SalesAgent:
    """
    Manages the chat logic, state, and business operations for the sales agent.
    This represents the core modules: NLU, Lead Management, Negotiation Engine, etc.
    """

    def __init__(self, session_state):
        """Initialize the agent with the current Streamlit session state."""
        self.ss = session_state
        self._initialize_state()

    def _initialize_state(self):
        """Set up default values in the session state if they don't exist."""
        defaults = {
            "history": [],
            "negotiation_context": None,
            "user_profile": {"name": "", "email": "", "country": "", "budget": (1_000_000, 3_000_000)},
            "filters": {"make": "", "year": (2018, 2024)},
            "currency": "PKR",
            "chat_started": False,
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)
        
        # Load inventory data once and cache it in the session state.
        if "inventory_df" not in self.ss:
            self.ss.inventory_df = self._load_inventory()
            self.ss.price_history_df = self._simulate_price_history()


    @st.cache_data
    def _load_inventory(_self):
        """
        Loads inventory from a remote CSV or generates dummy data as a fallback.
        This represents the "Knowledge Base" module.
        """
        try:
            df = pd.read_csv(DUMMY_INVENTORY_URL)
            # Basic data cleaning
            df = df.dropna(subset=['make', 'model', 'year', 'price'])
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
            df['price'] = pd.to_numeric(df['price'], errors='coerce').astype('Int64')
            return df
        except Exception as e:
            st.warning(f"Could not load live inventory (Error: {e}). Using dummy data.")
            # Fallback to dummy data generation
            inv = []
            for _ in range(500):
                make = random.choice(DUMMY_MAKES)
                model = random.choice(DUMMY_MODELS.get(make, ["Model"]))
                inv.append({
                    "year": random.randint(2015, 2024),
                    "make": make,
                    "model": model,
                    "price": random.randint(800_000, 8_000_000),
                    "location": random.choice(["Karachi", "Lahore", "Islamabad"]),
                    "image_url": f"https://placehold.co/600x400/grey/white?text={make}+{model}",
                    "id": f"VID{random.randint(1000,9999)}"
                })
            return pd.DataFrame(inv)

    @st.cache_data
    def _simulate_price_history(_self):
        """
        Simulates historical pricing data for the dynamic price graph feature.
        In a real app, this would come from a dedicated data source.
        """
        history = []
        inventory = _self._load_inventory()
        for _, car in inventory.iterrows():
            base_price = car['price']
            for year_offset in range(1, 6): # 5 years of history
                sim_year = car['year'] - year_offset
                if sim_year < 2015: continue
                # Simulate depreciation and market fluctuations
                price_fluctuation = 1 + (random.random() - 0.5) * 0.1 # +/- 5%
                sim_price = base_price * (0.85 ** year_offset) * price_fluctuation
                history.append({
                    "make": car['make'],
                    "model": car['model'],
                    "year": sim_year,
                    "avg_price": int(sim_price)
                })
        return pd.DataFrame(history)

    def add_message(self, role, content, ui_elements=None):
        """Adds a message to the chat history."""
        self.ss.history.append({"role": role, "content": content, "ui": ui_elements})
        if role == 'user':
            # Clear negotiation context if user types something unrelated.
            if self.ss.negotiation_context and not self._parse_intent(content)[0] in ['negotiate', 'accept_offer', 'reject_offer']:
                self.ss.negotiation_context = None

    def _parse_intent(self, user_input):
        """
        A simple intent recognition system.
        This is a basic implementation of the "Natural Language Understanding (NLU)" module.
        """
        text = user_input.lower()
        
        # 1. High-priority intents (deal acceptance, etc.)
        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "accept", "fine"]):
                return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another"]):
                return "reject_offer", {}

        # 2. Quick Actions
        if text == "show deals": return "show_deals", {}
        if text == "contact support": return "contact_support", {}

        # 3. Negotiation
        # Matches numbers like 2,500,000, 2.5m, 2500k, 25lakh
        money_match = re.search(r'(\d[\d,.]*)\s*(m|k|lakh|l)?', text)
        if money_match and self.ss.negotiation_context:
            val_str = money_match.group(1).replace(",", "")
            val = float(val_str)
            suffix = money_match.group(2)
            if suffix == 'm': val *= 1_000_000
            elif suffix == 'k': val *= 1_000
            elif suffix in ['lakh', 'l']: val *= 100_000
            return "negotiate", {"amount": int(val)}
        
        # 4. Vehicle Search Intent
        # Extracts Make, Model (optional), and Year (optional)
        # E.g., "toyota corolla 2020", "honda civic", "show me a 2018 camry"
        year_match = re.search(r'\b(20\d{2})\b', text)
        year = int(year_match.group(1)) if year_match else None
        
        makes_pattern = r'\b(' + '|'.join(re.escape(m.lower()) for m in DUMMY_MAKES) + r')\b'
        make_match = re.search(makes_pattern, text)
        make = make_match.group(1).capitalize() if make_match else None
        
        model = None
        if make:
            models_pattern = r'\b(' + '|'.join(re.escape(m.lower()) for m in DUMMY_MODELS.get(make, [])) + r')\b'
            model_match = re.search(models_pattern, text)
            if model_match:
                model = model_match.group(1).capitalize()

        if make or model or year:
            return "search_vehicle", {"make": make, "model": model, "year": year}
        
        # Fallback intent
        return "unknown", {}

    def respond(self, user_input):
        """
        Generates and adds a response to the user's input based on parsed intent.
        This is the main logic loop for the agent.
        """
        self.add_message("user", user_input)
        intent, params = self._parse_intent(user_input)

        # --- Handle each intent ---
        if intent == "search_vehicle":
            self._handle_search_vehicle(params)
        elif intent == "show_deals":
            self._handle_show_deals()
        elif intent == "contact_support":
            self.add_message("assistant", "You can reach our sales team at inquiry@otoz.ai or by calling +92-123-4567890.")
        elif intent == "negotiate":
            self._handle_negotiation(params['amount'])
        elif intent == "accept_offer":
            self._handle_accept_offer()
        elif intent == "reject_offer":
            self.add_message("assistant", "No problem. Let me know if you'd like to see other options. Just type 'show deals' or search for another car.")
            self.ss.negotiation_context = None
        else: # Fallback for "unknown" intent
            name = self.ss.user_profile.get("name", "").split(" ")[0]
            greeting = f"Hi {name}, " if name else ""
            self.add_message("assistant", f"{greeting}I can help you find a car. Try 'show deals' or search for a specific car, like 'Toyota Corolla 2020'.")

    def _handle_show_deals(self):
        """
        Finds and displays deals based on user profile and filters.
        This is part of the "Deal & Offer Management" module.
        """
        # Use budget from profile for smarter filtering
        min_budget, max_budget = self.ss.user_profile.get('budget', (0, 10_000_000))
        
        filtered_inventory = self.ss.inventory_df[
            (self.ss.inventory_df['price'] >= min_budget) &
            (self.ss.inventory_df['price'] <= max_budget)
        ]
        
        name = self.ss.user_profile.get("name", "").split(" ")[0]
        greeting = f"Okay {name}, " if name else ""
        
        if filtered_inventory.empty:
            self.add_message("assistant", f"{greeting}I couldn't find any deals matching your budget of PKR {min_budget:,} - {max_budget:,}. Try adjusting it in the sidebar.")
            return

        deals = filtered_inventory.sample(min(len(filtered_inventory), MAX_DEALS_TO_SHOW))
        
        self.add_message("assistant", f"{greeting}based on your budget, here are a few great options I found:")
        for _, car in deals.iterrows():
            self.add_message("assistant", "", ui_elements={"car_card": car.to_dict()})

    def _handle_search_vehicle(self, params):
        """
        Searches for a vehicle and displays results, including a price graph.
        """
        make, model, year = params.get("make"), params.get("model"), params.get("year")
        
        query_parts = [p for p in [make, model, str(year) if year else None] if p]
        self.add_message("assistant", f"Searching for: `{' '.join(query_parts)}`...")

        results = self.ss.inventory_df.copy()
        if make: results = results[results['make'].str.lower() == make.lower()]
        if model: results = results[results['model'].str.lower() == model.lower()]
        if year: results = results[results['year'] == year]

        if results.empty:
            self.add_message("assistant", "Sorry, I couldn't find any vehicles matching your search.")
            return

        # Display price history chart for the first found model
        # This is the "Dynamic Price Graph" feature
        main_model = results.iloc[0]['model']
        main_make = results.iloc[0]['make']
        
        history_data = self.ss.price_history_df[
            (self.ss.price_history_df['model'] == main_model) & 
            (self.ss.price_history_df['make'] == main_make)
        ]
        
        if not history_data.empty:
            chart_data = history_data.set_index('year')['avg_price']
            self.add_message("assistant", f"Here is the average price history for the **{main_make} {main_model}**:", ui_elements={"chart": chart_data})
        else:
             self.add_message("assistant", f"I couldn't find enough price history for the **{main_make} {main_model}** to create a graph.")
        
        # Display the top result
        top_car = results.iloc[0].to_dict()
        self.add_message("assistant", "Here's the best match I found:", ui_elements={"car_card": top_car})
        
        # Start negotiation
        self.ss.negotiation_context = {
            "car": top_car,
            "original_price": top_car['price'],
            "step": "initial"
        }
        price_str = self._format_price(top_car['price'])
        self.add_message("assistant", f"This vehicle is listed at **{price_str}**. It's a great deal, but I might be able to get you a better price. What's your best offer?")

    def _handle_negotiation(self, offer_amount):
        """
        Manages the back-and-forth of price negotiation.
        This is the "Negotiation Engine" module.
        """
        if not self.ss.negotiation_context:
            self.add_message("assistant", "I'm sorry, what were we negotiating? Please select a car first.")
            return
        
        ctx = self.ss.negotiation_context
        price = ctx['original_price']
        
        # Define negotiation thresholds
        floor_price = price * (1 - NEGOTIATION_MAX_DISCOUNT) # The absolute lowest we can go
        good_offer_threshold = price * (1 - NEGOTIATION_MIN_DISCOUNT) # A reasonable offer
        
        if offer_amount >= price:
            self.add_message("assistant", "That's the asking price! We can close the deal right now. Just say 'deal' to confirm.")
            ctx['final_price'] = price
            ctx['step'] = 'accepted'
        elif offer_amount >= good_offer_threshold:
            self.add_message("assistant", f"You've got a deal! I can accept **{self._format_price(offer_amount)}**. Just say 'yes' or 'deal' to generate the invoice.")
            ctx['final_price'] = offer_amount
            ctx['step'] = 'accepted'
        elif offer_amount >= floor_price:
            # Counter-offer logic
            counter_offer = (offer_amount + good_offer_threshold) / 2
            counter_offer = int(counter_offer / 1000) * 1000 # Round to nearest 1000
            self.add_message("assistant", f"That's a bit low for us. My manager has authorized me to go as low as **{self._format_price(counter_offer)}**. Can we make a deal at that price?")
            ctx['final_price'] = counter_offer
            ctx['step'] = 'countered'
        else:
            self.add_message("assistant", f"I'm sorry, but that offer is too low. The best I can do for this vehicle is around **{self._format_price(floor_price)}**. Perhaps we can find another vehicle that better fits your budget?")
            self.ss.negotiation_context = None # End negotiation

    def _handle_accept_offer(self):
        """
        Finalizes the deal and prepares for invoicing.
        This is part of the "Closing the Deal" workflow step.
        """
        if not self.ss.negotiation_context or 'final_price' not in self.ss.negotiation_context:
            self.add_message("assistant", "Great! Let's finalize the details. Which offer are you accepting?")
            return
            
        ctx = self.ss.negotiation_context
        final_price = ctx['final_price']
        car = ctx['car']
        
        self.add_message("assistant", f"Excellent! We have a deal for the **{car['year']} {car['make']} {car['model']}** at **{self._format_price(final_price)}**.")
        
        if ENABLE_PDF_INVOICING:
            self.add_message("assistant", "I'm generating the invoice for you now...", ui_elements={"invoice_button": ctx})
        else:
            self.add_message("assistant", "Deal confirmed! To enable PDF invoices, please ask the developer to install the `fpdf` library (`pip install fpdf`).")
        
        # Reset negotiation for the next deal
        self.ss.negotiation_context = None

    def _format_price(self, price):
        """Formats a price in the user's selected currency."""
        currency = self.ss.currency
        rate = CURRENCIES.get(currency, 1)
        converted_price = int(price * rate)
        return f"{currency} {converted_price:,}"


# ======================================================================================
# 3. Streamlit UI Presentation Layer
# This part of the script is only responsible for rendering the UI.
# ======================================================================================

def render_ui():
    """Renders the entire Streamlit user interface."""
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.title(PAGE_TITLE)

    # Instantiate the agent. This also loads the data on first run.
    agent = SalesAgent(st.session_state)

    # Define layout
    sidebar_container = st.sidebar.container()
    chat_container = st.container()
    
    # --- Sidebar UI ---
    with sidebar_container:
        render_sidebar(agent)
    
    # --- Main Chat UI ---
    with chat_container:
        if agent.ss.chat_started:
            render_chat_history(agent)
            
            user_input = st.chat_input("Your message...")
            if user_input:
                agent.respond(user_input)
                st.rerun() # Rerun to display the new messages immediately
        else:
            st.info("👋 Welcome to your AI Sales Assistant! Please fill out your profile on the left and click 'Start Chat' to begin.")


def render_sidebar(agent):
    """Renders the sidebar for user profile and filters."""
    st.header("Lead Profile 📋")
    
    if not agent.ss.chat_started:
        if st.button("Start Chat", type="primary", use_container_width=True):
            agent.ss.chat_started = True
            agent.add_message("assistant", f"Welcome! I'm your personal AI sales agent. How can I help you today? You can start by asking me to 'show deals'.")
            st.rerun()

    profile = agent.ss.user_profile
    profile['name'] = st.text_input("Name", profile['name'])
    profile['email'] = st.text_input("Email", profile['email'])
    profile['country'] = st.text_input("Country", profile['country'])
    profile['budget'] = st.slider("Budget (PKR)", 500_000, 10_000_000, profile['budget'])
    
    agent.ss.currency = st.selectbox("Display Prices in", list(CURRENCIES.keys()), 
                                    list(CURRENCIES.keys()).index(agent.ss.currency))

    if st.button("Save Profile", use_container_width=True):
        # Placeholder for CRM integration
        # update_crm(agent.ss.user_profile)
        st.success("Profile saved!")

    st.markdown("---")
    st.header("Quick Actions")
    if st.button("Show Available Deals", use_container_width=True):
        agent.respond("show deals")
        st.rerun()
    if st.button("Contact Human Support", use_container_width=True):
        agent.respond("contact support")
        st.rerun()


def render_chat_history(agent):
    """Renders the chat messages and any special UI elements."""
    for msg in agent.ss.history:
        avatar = BOT_AVATAR_URL if msg['role'] == 'assistant' else USER_AVATAR_URL
        with st.chat_message(msg['role'], avatar=avatar):
            st.markdown(msg['content'])
            
            # Render special UI elements if they exist
            if msg.get("ui"):
                ui_elements = msg["ui"]
                if "car_card" in ui_elements:
                    render_car_card(agent, ui_elements["car_card"])
                if "chart" in ui_elements:
                    st.line_chart(ui_elements["chart"])
                if "invoice_button" in ui_elements:
                    render_invoice_button(agent, ui_elements["invoice_button"])


def render_car_card(agent, car):
    """Renders a single vehicle as a visually appealing card."""
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(car['image_url'], use_column_width=True)
        with c2:
            st.subheader(f"{car['year']} {car['make']} {car['model']}")
            st.markdown(f"**Price:** {agent._format_price(car['price'])}")
            st.markdown(f"**Location:** {car['location']}")
            st.markdown(f"**Vehicle ID:** {car['id']}")
        
        # Button to start negotiation for this specific car
        if st.button(f"Make an Offer on this {car['model']}", key=f"offer_{car['id']}", use_container_width=True):
            agent.ss.negotiation_context = {
                "car": car,
                "original_price": car['price'],
                "step": "initial"
            }
            agent.add_message("assistant", f"Great choice! The listed price for the **{car['year']} {car['make']} {car['model']}** is **{agent._format_price(car['price'])}**. What is your opening offer?")
            st.rerun()


def render_invoice_button(agent, context):
    """Renders a download button for the PDF invoice."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Header
    pdf.cell(0, 10, PAGE_TITLE, ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, "INVOICE", ln=True, align='C')
    pdf.ln(10)
    
    # Customer and Car Details
    car = context['car']
    final_price = context['final_price']
    user = agent.ss.user_profile
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 8, "Billed To:", ln=False, border=1)
    pdf.cell(95, 8, "Vehicle Details:", ln=True, border=1)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"{user.get('name', 'N/A')}", ln=False, border=1)
    pdf.cell(95, 8, f"{car['year']} {car['make']} {car['model']}", ln=True, border=1)

    pdf.cell(95, 8, f"{user.get('email', 'N/A')}", ln=False, border=1)
    pdf.cell(95, 8, f"Vehicle ID: {car['id']}", ln=True, border=1)
    
    pdf.cell(95, 8, f"Country: {user.get('country', 'N/A')}", ln=False, border=1)
    pdf.cell(95, 8, f"Location: {car['location']}", ln=True, border=1)
    
    pdf.ln(10)
    
    # Financials
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Final Agreed Price", ln=True, align='C', border=1)
    pdf.set_font("Arial", 'B', 14)
    price_str = agent._format_price(final_price)
    pdf.cell(0, 12, price_str, ln=True, align='C', border=1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, f"Invoice generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')

    # Encode PDF to bytes for download button
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    st.download_button(
        label="📥 Download Invoice PDF",
        data=pdf_bytes,
        file_name=f"invoice_{car['id']}.pdf",
        mime="application/pdf"
    )

# ======================================================================================
# 4. Main App Execution
# ======================================================================================

if __name__ == "__main__":
    render_ui()
