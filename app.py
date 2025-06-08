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
SELLER_INFO = {
    "name": "Otoz.ai",
    "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678",
    "email": "sales@otoz.ai"
}


# --- UI Constants ---
BOT_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
USER_AVATAR_URL = "https://cdn-icons-png.flaticon.com/512/456/456212.png"

# --- Business Logic Constants (JAPAN-FOCUSED) ---
CURRENCIES = {"JPY": 1, "USD": 1/155, "PKR": 1/0.55} # JPY is the base currency
DUMMY_LOCATIONS = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]
MAX_DEALS_TO_SHOW = 3
NEGOTIATION_MIN_DISCOUNT = 0.05
NEGOTIATION_MAX_DISCOUNT = 0.12
MILEAGE_RANGE = (5_000, 150_000)
BUDGET_RANGE_JPY = (500_000, 15_000_000)


# ======================================================================================
# 2. Agentic Core Logic (SalesAgent Class)
# ======================================================================================

class SalesAgent:
    def __init__(self, session_state):
        self.ss = session_state
        self._initialize_state()

    def _initialize_state(self):
        defaults = {
            "history": [], "negotiation_context": None, "last_deal_context": None,
            "user_profile": {"name": "", "email": "", "country": "", "budget": (1_500_000, 5_000_000)},
            "filters": {"make": "", "model": "", "year": (2018, 2024), "mileage": MILEAGE_RANGE, "fuel": "", "transmission": ""},
            "currency": "JPY", "chat_started": False,
            "uploaded_inventory": None
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)
        if "inventory_df" not in self.ss or self.ss.get("data_source_is_dummy"):
            inventory = self._load_inventory()
            if inventory is not None:
                self.ss.inventory_df = inventory
                self.ss.price_history_df = self._simulate_price_history(inventory)

    @st.cache_data
    def _load_inventory(_self):
        # --- NEW: Prioritize uploaded file ---
        if _self.ss.uploaded_inventory is not None:
            try:
                st.info("Loading data from your uploaded file...")
                # Use pandas to read either Excel or CSV
                if ".csv" in _self.ss.uploaded_inventory.name:
                    df = pd.read_csv(_self.ss.uploaded_inventory)
                else:
                    df = pd.read_excel(_self.ss.uploaded_inventory)
                
                # Standardize column names from the uploaded file
                rename_map = {
                    'Make': 'make', 'Model': 'model', 'Year': 'year', 
                    'Price': 'price', 'Mileage': 'mileage', 'Fuel': 'fuel',
                    'Transmission': 'transmission'
                }
                df.rename(columns=lambda c: rename_map.get(c, c.lower()), inplace=True)

                required_cols = ['make', 'model', 'year', 'price']
                for col in required_cols:
                    if col not in df.columns:
                        st.error(f"Your file is missing the required column: '{col.title()}'")
                        return _self._generate_dummy_inventory("Error: Missing columns in uploaded file.")
                
                _self.ss["data_source_is_dummy"] = False
            except Exception as e:
                st.error(f"Could not read the uploaded file. Please ensure it's a valid CSV or Excel file. Error: {e}")
                return _self._generate_dummy_inventory("Error: Could not read uploaded file.")
        else:
            df = _self._generate_dummy_inventory()
            _self.ss["data_source_is_dummy"] = True

        # --- Data Cleaning & Transformation (applies to both uploaded and dummy data) ---
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df.dropna(subset=['price'], inplace=True)
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
        df.dropna(subset=['year'], inplace=True)
        
        if 'mileage' not in df.columns: df['mileage'] = [random.randint(MILEAGE_RANGE[0], MILEAGE_RANGE[1]) for _ in range(len(df))]
        if 'location' not in df.columns: df['location'] = [random.choice(DUMMY_LOCATIONS) for _ in range(len(df))]
        if 'fuel' not in df.columns: df['fuel'] = [random.choice(['Petrol', 'Hybrid', 'Diesel']) for _ in range(len(df))]
        if 'transmission' not in df.columns: df['transmission'] = [random.choice(['Automatic', 'Manual']) for _ in range(len(df))]
        
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={str(r.make).replace(' ','+')}+{str(r.model).replace(' ','+')}" for r in df.itertuples()]
        df.reset_index(drop=True, inplace=True)
        df['id'] = [f"VID{i:04d}" for i in df.index]
        return df

    def _generate_dummy_inventory(self, reason=""):
        if reason: st.warning(f"{reason} Using sample JDM inventory for this session.")
        car_data = [
            {'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000, 'fuel': 'Hybrid', 'transmission': 'Automatic'},
            {'make': 'Toyota', 'model': 'Prius', 'year': 2019, 'price': 1200000, 'fuel': 'Hybrid', 'transmission': 'Automatic'},
            {'make': 'Toyota', 'model': 'Vitz', 'year': 2017, 'price': 750000, 'fuel': 'Petrol', 'transmission': 'Automatic'},
            {'make': 'Honda', 'model': 'Fit', 'year': 2018, 'price': 800000, 'fuel': 'Hybrid', 'transmission': 'Automatic'},
            {'make': 'Honda', 'model': 'Vezel', 'year': 2019, 'price': 1500000, 'fuel': 'Hybrid', 'transmission': 'Automatic'},
            {'make': 'Nissan', 'model': 'Note', 'year': 2020, 'price': 950000, 'fuel': 'Hybrid', 'transmission': 'Automatic'},
        ]
        df = pd.DataFrame(car_data * 20)
        df.reset_index(drop=True, inplace=True)
        return df

    @st.cache_data
    def _simulate_price_history(_self, inventory_df):
        history = []
        today = pd.to_datetime(datetime.now())
        for _, car in inventory_df.iterrows():
            base_price = car['price']
            for month_offset in range(1, 13):
                sim_date, price_fluctuation = today - DateOffset(months=month_offset), 1 + (random.random() - 0.5) * 0.05
                sim_price = base_price * (0.992 ** month_offset) * price_fluctuation
                history.append({"make": car['make'], "model": car['model'], "date": sim_date, "avg_price": int(sim_price)})
        return pd.DataFrame(history)

    def add_message(self, role, content, ui_elements=None):
        self.ss.history.append({"role": role, "content": content, "ui": ui_elements})
    
    def _parse_intent(self, user_input):
        text = user_input.lower().strip()
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you']
        if any(word in text for word in greeting_words): return "greeting", {}
        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "i agree", "accept", "fine"]): return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another", "cancel"]): return "reject_offer", {}
            if any(w in text for w in ["discount", "best price", "negotiate"]): return "discount_inquiry", {}
            if any(w in text for w in ["what", "why", "don't understand"]): return "clarification_request", {}
        if any(w in text for w in ["invoice", "bill", "receipt"]): return "request_invoice", {}
        if text == "show deals": return "show_deals", {}
        if text == "contact support": return "contact_support", {}
        money_match = re.search(r'(\d[\d,.]*)\s*(m|k|lakh|l|million)?', text)
        if money_match and self.ss.negotiation_context:
            val_str = money_match.group(1).replace(",", "")
            val, suffix = float(val_str), money_match.group(2)
            if val < 1000 and suffix in ['m', 'million']: val *= 1_000_000
            elif suffix == 'k': val *= 1_000
            elif suffix in ['lakh', 'l']: val *= 100_000
            offer_in_base_currency = val / CURRENCIES.get(self.ss.currency, 1)
            return "negotiate", {"amount": int(offer_in_base_currency)}
        all_known_makes = list(self.ss.inventory_df['make'].unique())
        year_match, make, model = re.search(r'\b(20\d{2})\b', text), None, None
        year = int(year_match.group(1)) if year_match else None
        make_match = re.search(r'\b(' + '|'.join(re.escape(m.lower()) for m in all_known_makes) + r')\b', text)
        if make_match:
            make = make_match.group(1).title()
            all_known_models = list(self.ss.inventory_df[self.ss.inventory_df['make'] == make]['model'].unique())
            model_match = re.search(r'\b(' + '|'.join(re.escape(m.lower()) for m in all_known_models) + r')\b', text)
            if model_match: model = model_match.group(1).title()
        if make or model or year: return "search_vehicle", {"make": make, "model": model, "year": year}
        return "unknown", {}

    def respond(self, user_input):
        self.add_message("user", user_input)
        intent, params = self._parse_intent(user_input)
        handlers = {"greeting": self._handle_greeting, "search_vehicle": self._handle_search_vehicle, "show_deals": self._handle_show_deals, "negotiate": self._handle_negotiation, "accept_offer": self._handle_accept_offer, "reject_offer": self._handle_reject_offer, "request_invoice": self._handle_request_invoice, "discount_inquiry": self._handle_discount_inquiry, "clarification_request": self._handle_clarification}
        handler = handlers.get(intent)
        if handler:
            if intent == "search_vehicle": handler(params)
            elif intent == "negotiate": handler(params['amount'])
            else: handler()
        elif intent == "contact_support":
            self.add_message("assistant", f"You can reach our sales team at {SELLER_INFO['email']} or by calling {SELLER_INFO['phone']}.")
        else:
            self.add_message("assistant", f"I appreciate you asking! My expertise is in helping you find the perfect vehicle. How can I assist with your car search? You can say 'show deals' or search for a specific model.")

    def _handle_greeting(self):
        name = self.ss.user_profile.get("name", "").split(" ")[0]
        self.add_message("assistant", f"Hello {name if name else 'there'}! I'm {BOT_NAME}, your personal sales assistant from Otoz.ai. How can I help you find a vehicle today? You can start by saying 'show deals'.")

    def _handle_reject_offer(self):
        self.add_message("assistant", "No problem at all. Let's find something else. You can either adjust the filters on the left or just tell me what you're looking for.")
        self.ss.negotiation_context = None
        
    def _handle_clarification(self):
        if not self.ss.negotiation_context: self._handle_greeting(); return
        ctx = self.ss.negotiation_context
        car_name = f"{ctx['car']['year']} {ctx['car']['make']} {ctx['car']['model']}"
        if ctx.get('last_agent_offer'): self.add_message("assistant", f"My apologies if I was unclear. For the {car_name}, my current best offer is **{self._format_price(ctx['last_agent_offer'])}**. Can we agree on this price?")
        else: self.add_message("assistant", f"My apologies. We are currently discussing the {car_name}. The listed price is **{self._format_price(ctx['original_price'])}**. Please feel free to make an offer.")

    def _handle_request_invoice(self):
        if self.ss.last_deal_context:
            if ENABLE_PDF_INVOICING: self.add_message("assistant", "Of course, here is the invoice for your recent purchase.", ui_elements={"invoice_button": self.ss.last_deal_context})
            else: self.add_message("assistant", "I can confirm your deal is complete, but PDF invoice generation is currently disabled. The 'fpdf' library needs to be installed by the developer.")
        else: self.add_message("assistant", "I don't have a completed deal on record to create an invoice for. Please finalize a deal first.")

    def _handle_show_deals(self):
        self.ss.negotiation_context = None 
        min_budget, max_budget = self.ss.user_profile.get('budget', BUDGET_RANGE_JPY)
        min_year, max_year = self.ss.filters.get('year', (2015, 2025))
        min_mileage, max_mileage = self.ss.filters.get('mileage', MILEAGE_RANGE)
        make, model = self.ss.filters.get('make'), self.ss.filters.get('model')
        fuel, transmission = self.ss.filters.get('fuel'), self.ss.filters.get('transmission')
        results = self.ss.inventory_df[(self.ss.inventory_df['price'].between(min_budget, max_budget)) & (self.ss.inventory_df['year'].between(min_year, max_year)) & (self.ss.inventory_df['mileage'].between(min_mileage, max_mileage))]
        if make: results = results[results['make'] == make]
        if model: results = results[results['model'] == model]
        if fuel: results = results[results['fuel'] == fuel]
        if transmission: results = results[results['transmission'] == transmission]
        if results.empty: self.add_message("assistant", f"Okay {self.ss.user_profile.get('name', 'there')}, I couldn't find any deals matching your criteria. Try adjusting the filters."); return
        deals = results.sample(min(len(results), MAX_DEALS_TO_SHOW))
        self.add_message("assistant", f"Okay {self.ss.user_profile.get('name', 'there')}, based on your filters, here are a few great options:")
        for _, car in deals.iterrows(): self.add_message("assistant", "", ui_elements={"car_card": car.to_dict()})

    def _handle_search_vehicle(self, params):
        self.ss.negotiation_context = None 
        make, model, year = params.get("make"), params.get("model"), params.get("year")
        if make and not model and not year:
            self.add_message("assistant", f"We have many {make} vehicles in our inventory! To help me find the perfect one for you, could you please provide a bit more information? For example:")
            self.add_message("assistant", "• Are you interested in a specific **model** (like a Corolla or Civic)?\n• Do you have a preferred **year range**?\n• What kind of **budget** do you have in mind?")
            return
        query_parts = [p for p in [make, model, str(year) if year else None] if p]
        self.add_message("assistant", f"Searching for: `{' '.join(query_parts)}`...")
        results = self.ss.inventory_df.copy()
        if make: results = results[results['make'].str.lower() == make.lower()]
        if model: results = results[results['model'].str.lower() == model.lower()]
        if year: results = results[results['year'] == year]
        if results.empty: self.add_message("assistant", "Sorry, I couldn't find any vehicles matching your search."); return
        top_car = results.iloc[0].to_dict()
        self.add_message("assistant", "Here's the best match I found:", ui_elements={"car_card": top_car})
        self.initiate_negotiation(top_car)

    def initiate_negotiation(self, car_data):
        original_price = car_data['price']
        floor_price = original_price * (1 - NEGOTIATION_MAX_DISCOUNT)
        self.ss.negotiation_context = {"car": car_data, "original_price": original_price, "floor_price": floor_price, "step": "initial", "last_agent_offer": None}
        self.add_message("assistant", f"This {car_data['year']} {car_data['make']} {car_data['model']} is a great vehicle. The listed price is **{self._format_price(original_price)}**. What would be your opening offer?")

    def _handle_discount_inquiry(self):
        if not self.ss.negotiation_context: self.add_message("assistant", "I can definitely look into discounts for you. Which car are you interested in?"); return
        ctx = self.ss.negotiation_context
        price = ctx['original_price']
        opening_discount_price = int((price * 0.97) / 1000) * 1000
        self.add_message("assistant", f"I understand completely. For a serious buyer, I can start by offering a special price of **{self._format_price(opening_discount_price)}**. How does that sound as a starting point?")
        ctx.update({'last_agent_offer': opening_discount_price, 'step': 'countered'})

    def _handle_negotiation(self, offer_amount_base):
        if not self.ss.negotiation_context: return
        ctx = self.ss.negotiation_context
        price, floor_price = ctx['original_price'], ctx['floor_price']
        if ctx.get('last_agent_offer') and offer_amount_base >= ctx['last_agent_offer']:
             self.add_message("assistant", f"That's a fantastic offer! Let's make it official. I can accept **{self._format_price(offer_amount_base)}**. To confirm, just say 'I agree'.")
             ctx.update({'final_price': offer_amount_base, 'step': 'accepted'}); return
        if offer_amount_base >= price:
            self.add_message("assistant", f"That's the asking price, and I can certainly accept that! To confirm the deal at **{self._format_price(price)}**, just say 'I agree'.")
            ctx.update({'final_price': price, 'step': 'accepted'})
        elif offer_amount_base >= floor_price:
            counter_offer = int(((offer_amount_base + price) / 2) / 1000) * 1000
            if counter_offer >= price: counter_offer = int((price * 0.98)/1000) * 1000
            if counter_offer <= offer_amount_base: counter_offer = int((offer_amount_base * 1.02)/1000) * 1000
            self.add_message("assistant", f"Thank you, that's a strong offer. I have some flexibility and can meet you at **{self._format_price(counter_offer)}**. This is a great price for this vehicle. What do you think?")
            ctx.update({'final_price': counter_offer, 'step': 'countered', 'last_agent_offer': counter_offer})
        else:
            self.add_message("assistant", f"I appreciate your offer. For this particular vehicle, the absolute best I can do is **{self._format_price(floor_price)}**. If that works for you, we have a deal.")
            ctx.update({'final_price': floor_price, 'step': 'countered', 'last_agent_offer': floor_price})

    def _handle_accept_offer(self):
        if not self.ss.negotiation_context: self.add_message("assistant", "Great! What are we making a deal on? Please select a car first."); return
        ctx, price_to_accept = self.ss.negotiation_context, self.ss.negotiation_context.get('final_price')
        if price_to_accept:
            car = ctx['car']; ctx['final_price'] = price_to_accept
            self.add_message("assistant", f"Excellent! Deal confirmed for the **{car['year']} {car['make']} {car['model']}** at **{self._format_price(price_to_accept)}**.", ui_elements={"invoice_button": ctx} if ENABLE_PDF_INVOICING else None)
            self.ss.last_deal_context, self.ss.negotiation_context = ctx.copy(), None
        else: self.add_message("assistant", "I'm glad you're ready to make a deal! What final price are we agreeing on?")

    def _format_price(self, price_base):
        return f"{self.ss.currency} {int(price_base * CURRENCIES.get(self.ss.currency, 1)):,}"

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
    else: st.info(f"👋 Welcome! I'm {BOT_NAME}. Please fill out your profile and click 'Start Chat' to begin.")

def render_sidebar(agent):
    with st.sidebar:
        st.header("Lead Profile 📋")
        if not agent.ss.chat_started:
            if st.button("Start Chat", type="primary", use_container_width=True):
                agent.ss.chat_started, agent.ss.history = True, []
                agent.add_message("assistant", f"Welcome! I'm {BOT_NAME}, your personal AI sales agent. How can I help?")
                st.rerun()
        
        uploaded_file = st.file_uploader("Upload Your Inventory (Excel/CSV)", type=['xlsx', 'xls', 'csv'])
        if uploaded_file and uploaded_file != agent.ss.get("uploaded_inventory"):
            agent.ss.uploaded_inventory = uploaded_file
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        profile, filters = agent.ss.user_profile, agent.ss.filters
        profile['name'] = st.text_input("Name", profile.get('name', ''))
        profile['email'] = st.text_input("Email", profile.get('email', ''))
        profile['country'] = st.text_input("Country", profile.get('country', ''))
        profile['budget'] = st.slider("Budget (JPY)", BUDGET_RANGE_JPY[0], BUDGET_RANGE_JPY[1], profile.get('budget', (1_500_000, 5_000_000)))
        agent.ss.currency = st.selectbox("Display Prices in", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(agent.ss.currency))
        st.markdown("---")
        st.header("Vehicle Filters 🔎")
        all_makes = [""] + sorted(list(agent.ss.inventory_df['make'].unique()))
        make_index = all_makes.index(filters['make']) if filters.get('make') in all_makes else 0
        filters['make'] = st.selectbox("Make", all_makes, index=make_index)
        models = [""]
        if filters.get('make'): models.extend(sorted(list(agent.ss.inventory_df[agent.ss.inventory_df['make'] == filters['make']]['model'].unique())))
        model_index = models.index(filters['model']) if filters.get('model') in models else 0
        filters['model'] = st.selectbox("Model", models, index=model_index)
        filters['year'] = st.slider("Year Range", 2015, 2025, filters['year'])
        filters['mileage'] = st.slider("Mileage Range (km)", MILEAGE_RANGE[0], MILEAGE_RANGE[1], filters['mileage'])
        filters['fuel'] = st.selectbox("Fuel Type", [""] + sorted(list(agent.ss.inventory_df['fuel'].unique())))
        filters['transmission'] = st.selectbox("Transmission", [""] + sorted(list(agent.ss.inventory_df['transmission'].unique())))
        st.markdown("---")
        if st.button("Apply Filters & Show Deals", use_container_width=True):
            agent.respond("show deals")
            st.rerun()

def render_chat_history(agent):
    for i, msg in enumerate(agent.ss.history):
        avatar = BOT_AVATAR_URL if msg['role'] == 'assistant' else USER_AVATAR_URL
        with st.chat_message(msg['role'], avatar=avatar):
            st.markdown(msg['content'])
            if ui := msg.get("ui"):
                if "car_card" in ui: render_car_card(agent, ui["car_card"], i)
                if "invoice_button" in ui: render_invoice_button(agent, ui["invoice_button"], i)

def render_car_card(agent, car, message_key):
    with st.container(border=True):
        main_model, main_make = car['model'], car['make']
        price_df, currency, rate = agent.ss.price_history_df, agent.ss.currency, CURRENCIES.get(agent.ss.currency, 1)
        history_data = price_df[(price_df['model'] == main_model) & (price_df['make'] == main_make)]
        six_months_ago = pd.to_datetime(datetime.now()) - DateOffset(months=6)
        recent_history = history_data[history_data['date'] >= six_months_ago].copy()
        recent_history['display_price'] = recent_history['avg_price'] * rate
        if not recent_history.empty:
            chart = alt.Chart(recent_history).mark_area(line={'color':'#4A90E2'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='white', offset=0), alt.GradientStop(color='#4A90E2', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X('date:T', title='Date', axis=alt.Axis(format="%b %Y")), y=alt.Y('display_price:Q', title=f'Average Price ({currency})', scale=alt.Scale(zero=False)), tooltip=[alt.Tooltip('date:T', format='%B %Y'), alt.Tooltip('display_price:Q', format=',.0f')]).properties(title=f'6-Month Price Trend for {main_make} {main_model}').interactive()
            st.altair_chart(chart, use_container_width=True)
        c1, c2 = st.columns([1, 2])
        c1.image(car['image_url'], use_column_width=True)
        with c2:
            st.subheader(f"{car['year']} {car['make']} {car['model']}")
            st.markdown(f"**Price:** {agent._format_price(car['price'])}")
            st.markdown(f"**Mileage:** {car['mileage']:,} km"); st.markdown(f"**Location:** {car['location']}")
        if st.button(f"Make an Offer on this {car['model']}", key=f"offer_{car['id']}_{message_key}", use_container_width=True):
            agent.initiate_negotiation(car)
            st.rerun()

def render_invoice_button(agent, context, message_key):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, SELLER_INFO['name'], ln=True, align='C'); pdf.set_font("Arial", '', 12)
    pdf.cell(0, 5, SELLER_INFO['address'], ln=True, align='C')
    pdf.cell(0, 5, f"Phone: {SELLER_INFO['phone']} | Email: {SELLER_INFO['email']}", ln=True, align='C'); pdf.ln(10)
    car, final_price, user = context['car'], context['final_price'], agent.ss.user_profile
    pdf.set_font("Arial", 'B', 12); pdf.cell(95, 8, "Billed To:", 1); pdf.cell(95, 8, "Vehicle Details:", 1, ln=1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"{user.get('name', 'N/A')} ({user.get('email', 'N/A')})", 1)
    pdf.cell(95, 8, f"{car['year']} {car['make']} {car['model']}", 1, ln=1)
    pdf.cell(95, 8, f"Country: {user.get('country', 'N/A')}", 1); pdf.cell(95, 8, f"Vehicle ID: {car['id']}", 1, ln=1); pdf.ln(10)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "Final Agreed Price", 1, align='C', ln=1)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 12, agent._format_price(final_price), 1, align='C', ln=1); pdf.ln(10)
    pdf.set_font("Arial", 'I', 8); pdf.cell(0, 5, f"Invoice generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C', ln=1)
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button("📥 Download Invoice PDF", pdf_bytes, f"invoice_{car['id']}.pdf", "application/pdf", key=f"download_{car['id']}_{message_key}")

# ======================================================================================
# 4. Main App Execution
# ======================================================================================

if __name__ == "__main__":
    render_ui()

# End of script
