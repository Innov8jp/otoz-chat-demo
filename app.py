import re
import random
import altair as alt
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset

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
BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
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

# --- Business Logic Constants (JAPAN-FOCUSED) ---
CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55} # JPY is the base currency
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
DUMMY_MAKES = ["Toyota", "Honda", "Nissan", "Suzuki", "Mazda", "Subaru", "Mitsubishi", "Lexus"]
DUMMY_MODELS = {
    "Toyota": ["Corolla", "Camry", "RAV4", "Prius", "Yaris", "Hilux", "Fortuner", "Land Cruiser"],
    "Honda": ["Civic", "Accord", "CR-V", "Fit", "Jazz", "HR-V", "Odyssey", "Pilot"],
    "Nissan": ["Sentra", "Altima", "Rogue", "Versa", "Note", "Serena"],
    "Suzuki": ["Swift", "Alto", "Vitara", "Jimny"],
    "Mazda": ["Mazda3", "Mazda6", "CX-5", "CX-30"],
    "Subaru": ["Impreza", "Outback", "Forester", "Levorg"],
    "Mitsubishi": ["Lancer", "Outlander", "Pajero", "Delica"],
    "Lexus": ["IS", "ES", "RX", "NX"],
}
MAX_DEALS_TO_SHOW = 3
NEGOTIATION_MIN_DISCOUNT = 0.05  # 5%
NEGOTIATION_MAX_DISCOUNT = 0.12  # 12%
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 10_000_000)


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
            "user_profile": {"name": "", "email": "", "country": "", "budget": (1_500_000, 5_000_000)},
            "filters": {"make": "", "model": "", "year": (2018, 2024), "mileage": MILEAGE_RANGE},
            "currency": "JPY",
            "chat_started": False,
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)

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
            # Attempt to load live data first
            df = pd.read_csv(DUMMY_INVENTORY_URL, on_bad_lines='skip')
            df = df.dropna(subset=['make', 'model', 'year', 'price'])
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
            df['price'] = pd.to_numeric(df['price'], errors='coerce').astype('Int64')
            if 'mileage' not in df.columns:
                 df['mileage'] = [random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]) for _ in range(len(df))]
            return df
        except Exception:
            # Fallback to dummy data generation focused on Japan
            inv = []
            for i in range(1000): # Generate 1000 cars
                make = random.choice(DUMMY_MAKES)
                model = random.choice(DUMMY_MODELS.get(make, ["Model"]))
                inv.append({
                    "year": random.randint(2015, 2025),
                    "make": make,
                    "model": model,
                    "price": random.randint(BUDGET_RANGE_JPY[0], BUDGET_RANGE_JPY[1]),
                    "location": random.choice(DUMMY_LOCATIONS),
                    "mileage": random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]),
                    "image_url": f"https://placehold.co/600x400/grey/white?text={make}+{model}",
                    "id": f"VID{i:04d}" # FIX: Ensure unique ID to prevent key errors
                })
            return pd.DataFrame(inv)

    @st.cache_data
    def _simulate_price_history(_self):
        """
        Simulates monthly historical pricing data for the dynamic price graph feature.
        """
        history, inventory = [], _self._load_inventory()
        today = pd.to_datetime(datetime.now())

        for _, car in inventory.iterrows():
            base_price = car['price']
            for month_offset in range(1, 25): # 2 years of history to ensure we have 6 months of recent data
                sim_date = today - DateOffset(months=month_offset)
                price_fluctuation = 1 + (random.random() - 0.5) * 0.05
                sim_price = base_price * (0.992 ** month_offset) * price_fluctuation
                history.append({
                    "make": car['make'], "model": car['model'],
                    "date": sim_date, "avg_price": int(sim_price)
                })
        return pd.DataFrame(history)

    def add_message(self, role, content, ui_elements=None):
        """Adds a message to the chat history."""
        self.ss.history.append({"role": role, "content": content, "ui": ui_elements})
        if role == 'user' and self.ss.negotiation_context and self._parse_intent(content)[0] not in ['negotiate', 'accept_offer', 'reject_offer']:
            self.ss.negotiation_context = None

    def _parse_intent(self, user_input):
        """A simple intent recognition system (NLU module)."""
        text = user_input.lower()
        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "accept", "fine"]): return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another"]): return "reject_offer", {}
        if text == "show deals": return "show_deals", {}
        if text == "contact support": return "contact_support", {}
        money_match = re.search(r'(\d[\d,.]*)\s*(m|k|lakh|l)?', text)
        if money_match and self.ss.negotiation_context:
            val_str = money_match.group(1).replace(",", "")
            val, suffix = float(val_str), money_match.group(2)
            if suffix == 'm': val *= 1_000_000
            elif suffix == 'k': val *= 1_000
            elif suffix in ['lakh', 'l']: val *= 100_000
            offer_in_base_currency = val / CURRENCIES.get(self.ss.currency, 1)
            return "negotiate", {"amount": int(offer_in_base_currency)}
        year_match, make, model = re.search(r'\b(20\d{2})\b', text), None, None
        year = int(year_match.group(1)) if year_match else None
        makes_pattern = r'\b(' + '|'.join(re.escape(m.lower()) for m in DUMMY_MAKES) + r')\b'
        make_match = re.search(makes_pattern, text)
        if make_match:
            make = make_match.group(1).capitalize()
            models_pattern = r'\b(' + '|'.join(re.escape(m.lower()) for m in DUMMY_MODELS.get(make, [])) + r')\b'
            model_match = re.search(models_pattern, text)
            if model_match: model = model_match.group(1).capitalize()
        if make or model or year:
            return "search_vehicle", {"make": make, "model": model, "year": year}
        return "unknown", {}

    def respond(self, user_input):
        """Generates and adds a response to the user's input based on parsed intent."""
        self.add_message("user", user_input)
        intent, params = self._parse_intent(user_input)
        if intent == "search_vehicle": self._handle_search_vehicle(params)
        elif intent == "show_deals": self._handle_show_deals()
        elif intent == "contact_support": self.add_message("assistant", f"You can reach our sales team at inquiry@otoz.ai or by calling +81-3-1234-5678.")
        elif intent == "negotiate": self._handle_negotiation(params['amount'])
        elif intent == "accept_offer": self._handle_accept_offer()
        elif intent == "reject_offer":
            self.add_message("assistant", "No problem. Let me know if you'd like to see other options.")
            self.ss.negotiation_context = None
        else:
            name = self.ss.user_profile.get("name", "").split(" ")[0]
            greeting = f"Hi {name}, " if name else ""
            self.add_message("assistant", f"{greeting}I'm {BOT_NAME}. Try 'show deals' or search for a specific car, like 'Toyota Corolla 2020'.")

    def _handle_show_deals(self):
        """Finds and displays deals based on user profile and sidebar filters."""
        min_budget, max_budget = self.ss.user_profile.get('budget', BUDGET_RANGE_JPY)
        min_year, max_year = self.ss.filters.get('year', (2015, 2025))
        min_mileage, max_mileage = self.ss.filters.get('mileage', MILEAGE_RANGE)
        make, model = self.ss.filters.get('make'), self.ss.filters.get('model')
        results = self.ss.inventory_df[
            (self.ss.inventory_df['price'] >= min_budget) & (self.ss.inventory_df['price'] <= max_budget) &
            (self.ss.inventory_df['year'] >= min_year) & (self.ss.inventory_df['year'] <= max_year) &
            (self.ss.inventory_df['mileage'] >= min_mileage) & (self.ss.inventory_df['mileage'] <= max_mileage)
        ]
        if make and make != "All Makes": results = results[results['make'] == make]
        if model and model != "All Models": results = results[results['model'] == model]

        greeting = f"Okay {self.ss.user_profile.get('name', 'there')}, "
        if results.empty:
            self.add_message("assistant", f"{greeting}I couldn't find any deals matching your criteria. Try adjusting the filters.")
            return
        deals = results.sample(min(len(results), MAX_DEALS_TO_SHOW))
        self.add_message("assistant", f"{greeting}based on your filters, here are a few great options:")
        for _, car in deals.iterrows():
            self.add_message("assistant", "", ui_elements={"car_card": car.to_dict()})

    def _handle_search_vehicle(self, params):
        """Searches for a vehicle and displays results, including a price graph."""
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

        main_model, main_make = results.iloc[0]['model'], results.iloc[0]['make']
        history_data = self.ss.price_history_df[(self.ss.price_history_df['model'] == main_model) & (self.ss.price_history_df['make'] == main_make)]
        six_months_ago, currency, rate = pd.to_datetime(datetime.now()) - DateOffset(months=6), self.ss.currency, CURRENCIES.get(self.ss.currency, 1)
        recent_history = history_data[history_data['date'] >= six_months_ago].copy()
        recent_history['display_price'] = recent_history['avg_price'] * rate
        
        if not recent_history.empty:
            chart = alt.Chart(recent_history).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('display_price:Q', title=f'Average Price ({currency})', scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip('date:T', format='%B %Y'), alt.Tooltip('display_price:Q', format=',.0f')]
            ).properties(title=f'6-Month Price Trend for {main_make} {main_model}').interactive()
            self.add_message("assistant", "", ui_elements={"chart": chart})
        
        top_car = results.iloc[0].to_dict()
        self.add_message("assistant", "Here's the best match I found:", ui_elements={"car_card": top_car})
        self.ss.negotiation_context = {"car": top_car, "original_price": top_car['price'], "step": "initial"}
        self.add_message("assistant", f"This vehicle is listed at **{self._format_price(top_car['price'])}**. What's your best offer?")

    def _handle_negotiation(self, offer_amount_base):
        """Manages negotiation. Expects offer_amount in base currency (JPY)."""
        if not self.ss.negotiation_context: return
        ctx, price = self.ss.negotiation_context, self.ss.negotiation_context['original_price']
        floor_price, good_offer_threshold = price * (1 - NEGOTIATION_MAX_DISCOUNT), price * (1 - NEGOTIATION_MIN_DISCOUNT)
        if offer_amount_base >= price:
            self.add_message("assistant", f"That's the asking price! We can close the deal now at **{self._format_price(price)}**. Say 'deal' to confirm.")
            ctx.update({'final_price': price, 'step': 'accepted'})
        elif offer_amount_base >= good_offer_threshold:
            self.add_message("assistant", f"You've got a deal! I can accept **{self._format_price(offer_amount_base)}**. Say 'yes' or 'deal' to generate the invoice.")
            ctx.update({'final_price': offer_amount_base, 'step': 'accepted'})
        elif offer_amount_base >= floor_price:
            counter_offer = int(((offer_amount_base + good_offer_threshold) / 2) / 1000) * 1000
            self.add_message("assistant", f"That's a bit low. My manager authorized me to go as low as **{self._format_price(counter_offer)}**. Can we deal there?")
            ctx.update({'final_price': counter_offer, 'step': 'countered'})
        else:
            self.add_message("assistant", f"I'm sorry, that offer is too low. The best I can do is around **{self._format_price(floor_price)}**.")
            self.ss.negotiation_context = None

    def _handle_accept_offer(self):
        """Finalizes the deal."""
        if not self.ss.negotiation_context or 'final_price' not in self.ss.negotiation_context: return
        ctx, car = self.ss.negotiation_context, self.ss.negotiation_context['car']
        self.add_message("assistant", f"Excellent! Deal confirmed for the **{car['year']} {car['make']} {car['model']}** at **{self._format_price(ctx['final_price'])}**.")
        if ENABLE_PDF_INVOICING:
            self.add_message("assistant", "I'm generating the invoice...", ui_elements={"invoice_button": ctx})
        self.ss.negotiation_context = None

    def _format_price(self, price_base):
        """Formats a price in the user's selected currency."""
        rate = CURRENCIES.get(self.ss.currency, 1)
        return f"{self.ss.currency} {int(price_base * rate):,}"

# ======================================================================================
# 3. Streamlit UI Presentation Layer
# ======================================================================================

def render_ui():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.title(PAGE_TITLE)
    agent = SalesAgent(st.session_state)
    render_sidebar(agent)
    if agent.ss.chat_started:
        render_chat_history(agent)
        if user_input := st.chat_input("Your message..."):
            agent.respond(user_input)
            st.rerun()
    else:
        st.info(f"👋 Welcome! I'm {BOT_NAME}. Please fill out your profile and click 'Start Chat' to begin.")

def render_sidebar(agent):
    with st.sidebar:
        st.header("Lead Profile 📋")
        if not agent.ss.chat_started:
            if st.button("Start Chat", type="primary", use_container_width=True):
                agent.ss.chat_started = True
                agent.add_message("assistant", f"Welcome! I'm {BOT_NAME}, your personal AI sales agent. How can I help?")
                st.rerun()
        profile, filters = agent.ss.user_profile, agent.ss.filters
        profile['name'] = st.text_input("Name", profile.get('name', ''))
        profile['email'] = st.text_input("Email", profile.get('email', ''))
        profile['country'] = st.text_input("Country", profile.get('country', ''))
        profile['budget'] = st.slider("Budget (JPY)", BUDGET_RANGE_JPY[0], BUDGET_RANGE_JPY[1], profile.get('budget', (1_500_000, 5_000_000)))
        agent.ss.currency = st.selectbox("Display Prices in", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(agent.ss.currency))
        
        st.markdown("---")
        st.header("Vehicle Filters 🔎")
        all_makes, models = [""] + DUMMY_MAKES, [""]
        filters['make'] = st.selectbox("Make", all_makes, index=all_makes.index(filters['make']) if filters['make'] in all_makes else 0)
        if filters['make']: models.extend(DUMMY_MODELS.get(filters['make'], []))
        filters['model'] = st.selectbox("Model", models, index=models.index(filters['model']) if filters['model'] in models else 0)
        filters['year'] = st.slider("Year Range", 2015, 2025, filters['year'])
        filters['mileage'] = st.slider("Mileage Range (km)", MILEAGE_RANGE[0], MILEAGE_RANGE[1], filters['mileage'])

        st.markdown("---")
        if st.button("Apply Filters & Show Deals", use_container_width=True):
            agent.respond("show deals")
            st.rerun()

def render_chat_history(agent):
    # FIX: Use enumerate to get a unique index for each message to prevent key errors
    for i, msg in enumerate(agent.ss.history):
        avatar = BOT_AVATAR_URL if msg['role'] == 'assistant' else USER_AVATAR_URL
        with st.chat_message(msg['role'], avatar=avatar):
            st.markdown(msg['content'])
            if ui := msg.get("ui"):
                if "car_card" in ui: render_car_card(agent, ui["car_card"], message_key=i)
                if "chart" in ui: st.altair_chart(ui["chart"], use_container_width=True)
                if "invoice_button" in ui: render_invoice_button(agent, ui["invoice_button"], message_key=i)

def render_car_card(agent, car, message_key):
    # FIX: Add message_key to the button's key to ensure it's always unique
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        c1.image(car['image_url'], use_column_width=True)
        with c2:
            st.subheader(f"{car['year']} {car['make']} {car['model']}")
            st.markdown(f"**Price:** {agent._format_price(car['price'])}")
            st.markdown(f"**Mileage:** {car['mileage']:,} km")
            st.markdown(f"**Location:** {car['location']}")
        if st.button(f"Make an Offer on this {car['model']}", key=f"offer_{car['id']}_{message_key}", use_container_width=True):
            agent.ss.negotiation_context = {"car": car, "original_price": car['price'], "step": "initial"}
            agent.add_message("assistant", f"Great choice! Listed price is **{agent._format_price(car['price'])}**. What's your offer?")
            st.rerun()

def render_invoice_button(agent, context, message_key):
    # FIX: Add message_key to the download_button's key
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, PAGE_TITLE, ln=True, align='C'); pdf.set_font("Arial", '', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(10)
    car, final_price, user = context['car'], context['final_price'], agent.ss.user_profile
    pdf.set_font("Arial", 'B', 12); pdf.cell(95, 8, "Billed To:", 1); pdf.cell(95, 8, "Vehicle Details:", 1, ln=1)
    pdf.set_font("Arial", '', 10); pdf.cell(95, 8, f"{user.get('name', 'N/A')}", 1); pdf.cell(95, 8, f"{car['year']} {car['make']} {car['model']}", 1, ln=1)
    pdf.cell(95, 8, f"{user.get('email', 'N/A')}", 1); pdf.cell(95, 8, f"Vehicle ID: {car['id']}", 1, ln=1); pdf.ln(10)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "Final Agreed Price", 1, align='C', ln=1)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 12, agent._format_price(final_price), 1, align='C', ln=1); pdf.ln(10)
    pdf.set_font("Arial", 'I', 8); pdf.cell(0, 5, f"Invoice generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C', ln=1)
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button(
        label="📥 Download Invoice PDF",
        data=pdf_bytes,
        file_name=f"invoice_{car['id']}.pdf",
        mime="application/pdf",
        key=f"download_{car['id']}_{message_key}"
    )

# ======================================================================================
# 4. Main App Execution
# ======================================================================================

if __name__ == "__main__":
    render_ui()
