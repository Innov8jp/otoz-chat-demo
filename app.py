import re
import random
import altair as alt
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import os

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
            "filters": {"make": "", "model": "", "year": (2018, 2024), "mileage": MILEAGE_RANGE, "fuel": "", "transmission": "", "color": "", "grade": ""},
            "currency": "JPY", "chat_started": False,
            "query_context": {}, "search_results": [], "search_results_index": 0,
            "current_car_to_display": None, "data_source_name": "Internal Dummy Data",
            "invoice_to_render": None
        }
        for key, value in defaults.items():
            self.ss.setdefault(key, value)
        if "inventory_df" not in self.ss:
            self._reload_data()

    def _reload_data(self):
        inventory = self._load_inventory()
        market_data = self._load_market_data()
        if inventory is not None:
            if market_data is not None:
                self.ss.inventory_df = pd.merge(inventory, market_data, on=['make', 'model', 'year'], how='left')
            else:
                self.ss.inventory_df = inventory
            self.ss.price_history_df = self._simulate_price_history(inventory)

    @st.cache_data
    def _load_inventory(_self):
        inventory_file_path = 'Inventory Agasta.csv'
        if os.path.exists(inventory_file_path):
            try:
                df = pd.read_csv(inventory_file_path)
                _self.ss.data_source_name = f"✅ Using: {inventory_file_path}"
                rename_map = {'Make': 'make', 'Model': 'model', 'Year': 'year', 'Price': 'price', 'Mileage': 'mileage', 'Fuel': 'fuel', 'Transmission': 'transmission', 'Color': 'color', 'Grade': 'grade'}
                df.rename(columns=lambda c: rename_map.get(c, c.lower()), inplace=True)
                required_cols = ['make', 'model', 'year', 'price']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"Your file is missing one or more required columns: Make, Model, Year, Price."); return _self._generate_dummy_inventory(fallback=True)
            except Exception as e:
                st.error(f"Could not read your inventory file. Error: {e}"); return _self._generate_dummy_inventory(fallback=True)
        else:
            df = _self._generate_dummy_inventory(); _self.ss.data_source_name = "⚠️ Using Internal Sample Data"
        df['price'] = pd.to_numeric(df['price'], errors='coerce'); df.dropna(subset=['price'], inplace=True)
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64'); df.dropna(subset=['year'], inplace=True)
        for col, default_values in [('mileage', MILEAGE_RANGE), ('location', DUMMY_LOCATIONS), ('fuel', ['Petrol', 'Hybrid', 'Diesel']), ('transmission', ['Automatic', 'Manual']), ('color', ['White', 'Black', 'Silver']), ('grade', ['4.5', 'S', '4', 'R'])]:
            if col not in df.columns: df[col] = [random.choice(default_values) if isinstance(default_values, list) else random.randint(default_values[0], default_values[1]) for _ in range(len(df))]
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={str(r.make).replace(' ','+')}+{str(r.model).replace(' ','+')}" for r in df.itertuples()]
        df.reset_index(drop=True, inplace=True); df['id'] = [f"VID{i:04d}" for i in df.index]
        return df

    def _generate_dummy_inventory(self, fallback=False):
        if fallback: st.warning("Reverting to internal sample JDM inventory.")
        car_data = [{'make': 'Toyota', 'model': 'Aqua', 'year': 2018, 'price': 850000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Silver', 'grade': '4.5'}, {'make': 'Toyota', 'model': 'Prius', 'year': 2019, 'price': 1200000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'White', 'grade': 'S'}, {'make': 'Honda', 'model': 'Fit', 'year': 2018, 'price': 800000, 'fuel': 'Hybrid', 'transmission': 'Automatic', 'color': 'Blue', 'grade': '4'}]
        return pd.DataFrame(car_data * 50)

    @st.cache_data
    def _load_market_data(_self):
        if os.path.exists(MARKET_DATA_FILE_PATH):
            try:
                _self.ss.market_prices_df = pd.read_csv(MARKET_DATA_FILE_PATH)
                st.sidebar.info("✅ Live market price data loaded.")
            except Exception as e:
                st.sidebar.warning(f"Could not load market data file: {e}"); _self.ss.market_prices_df = None
        else:
            st.sidebar.warning("⚠️ Market price data not found. Run `market_scraper.py` to generate it."); _self.ss.market_prices_df = None

    @st.cache_data
    def _simulate_price_history(_self, inventory_df):
        history = []; today = pd.to_datetime(datetime.now())
        for _, car in inventory_df.iterrows():
            base_price = car['price']
            for month_offset in range(1, 13):
                sim_date, price_fluctuation = today - DateOffset(months=month_offset), 1 + (random.random() - 0.5) * 0.05
                sim_price = base_price * (0.992 ** month_offset) * price_fluctuation
                history.append({"make": car['make'], "model": car['model'], "date": sim_date, "avg_price": int(sim_price)})
        return pd.DataFrame(history)

    def add_message(self, role, content):
        self.ss.history.append({"role": role, "content": content})
    
    def _parse_intent(self, user_input):
        text = user_input.lower().strip()
        if text in ['hello', 'hi', 'hey']: return "greeting", {}
        if self.ss.negotiation_context:
            if any(w in text for w in ["deal", "yes", "ok", "i agree", "accept", "fine"]): return "accept_offer", {}
            if any(w in text for w in ["no", "pass", "another", "cancel"]): return "reject_offer", {}
            if any(w in text for w in ["discount", "best price", "negotiate"]): return "discount_inquiry", {}
            money_match = re.search(r'(\d[\d,.]*)\s*(m|k|lakh|l|million)?', text)
            if money_match:
                val_str, (val, suffix) = money_match.group(1).replace(",", ""), (float(money_match.group(1).replace(",", "")), money_match.group(2))
                if val < 1000 and suffix in ['m', 'million']: val *= 1_000_000
                elif suffix == 'k': val *= 1_000
                elif suffix in ['lakh', 'l']: val *= 100_000
                return "negotiate", {"amount": int(val / CURRENCIES.get(self.ss.currency, 1))}
        if any(w in text for w in ["invoice", "bill", "receipt"]): return "request_invoice", {}
        if text == "show deals": return "show_deals", {}
        if text == "contact support": return "contact_support", {}
        all_known_makes = list(self.ss.inventory_df['make'].unique())
        makes_pattern = r'\b(' + '|'.join(re.escape(m.lower()) + r's?' for m in all_known_makes) + r')\b'
        make_match = re.search(makes_pattern, text)
        make = make_match.group(1).replace('s', '').title() if make_match else self.ss.query_context.get('make')
        model = None
        if make:
            all_known_models = list(self.ss.inventory_df[self.ss.inventory_df['make'] == make]['model'].unique())
            model_match = re.search(r'\b(' + '|'.join(re.escape(m.lower()) for m in all_known_models) + r')\b', text)
            if model_match: model = model_match.group(1).title()
        year = int(re.search(r'\b(20\d{2})\b', text).group(1)) if re.search(r'\b(20\d{2})\b', text) else None
        color = re.search(r'\b(white|black|silver|blue|red|grey|orange)\b', text).group(1).title() if re.search(r'\b(white|black|silver|blue|red|grey|orange)\b', text) else None
        if make or model or year or color:
            if make: self.ss.query_context['make'] = make
            if model: self.ss.query_context['model'] = model
            if year: self.ss.query_context['year'] = year
            if color: self.ss.query_context['color'] = color
            return "search_vehicle", self.ss.query_context
        return "unknown", {}

    def respond(self, user_input):
        self.add_message("user", user_input)
        intent, params = self._parse_intent(user_input)
        handlers = {"greeting": self._handle_greeting, "search_vehicle": self._handle_search_vehicle, "show_deals": self._handle_show_deals, "show_next_deal": self._handle_show_next_deal, "negotiate": self._handle_negotiation, "accept_offer": self._handle_accept_offer, "reject_offer": self._handle_reject_offer, "request_invoice": self._handle_request_invoice, "discount_inquiry": self._handle_discount_inquiry}
        handler = handlers.get(intent)
        if handler:
            if intent in ["search_vehicle", "negotiate"]: handler(params)
            else: handler()
        elif intent == "contact_support":
            self.add_message("assistant", f"You can reach our sales team at {SELLER_INFO['email']} or by calling {SELLER_INFO['phone']}.")
        else:
            self.add_message("assistant", f"I appreciate you asking! My expertise is in helping you find the perfect vehicle. How can I assist with your car search? You can say 'show deals' or search for a specific model.")

    def _handle_greeting(self):
        name = self.ss.user_profile.get("name", "").split(" ")[0]
        self.add_message("assistant", f"Hello {name if name else 'there'}! I'm {BOT_NAME}, your personal sales assistant from Otoz.ai. How can I help you find a vehicle today?")

    def _handle_reject_offer(self):
        self.add_message("assistant", "No problem at all. Let's find something else.")
        self.ss.negotiation_context = None
        self._handle_show_next_deal()

    def _handle_request_invoice(self):
        if self.ss.last_deal_context: self.ss.invoice_to_render = self.ss.last_deal_context
        else: self.add_message("assistant", "I don't have a completed deal on record to create an invoice for. Please finalize a deal first.")

    def _handle_show_deals(self):
        self.ss.negotiation_context = None 
        self.ss.query_context = {}
        min_budget, max_budget = self.ss.user_profile.get('budget', BUDGET_RANGE_JPY)
        min_year, max_year = self.ss.filters.get('year', (2015, 2025))
        min_mileage, max_mileage = self.ss.filters.get('mileage', MILEAGE_RANGE)
        make, model, fuel, transmission, color, grade = [self.ss.filters.get(k) for k in ['make', 'model', 'fuel', 'transmission', 'color', 'grade']]
        results = self.ss.inventory_df[(self.ss.inventory_df['price'].between(min_budget, max_budget)) & (self.ss.inventory_df['year'].between(min_year, max_year)) & (self.ss.inventory_df['mileage'].between(min_mileage, max_mileage))]
        if make: results = results[results['make'] == make]
        if model: results = results[results['model'] == model]
        if fuel: results = results[results['fuel'] == fuel]
        if transmission: results = results[results['transmission'] == transmission]
        if color: results = results[results['color'] == color]
        if grade: results = results[results['grade'] == grade]
        if results.empty: self.add_message("assistant", f"Okay {self.ss.user_profile.get('name', 'there')}, I couldn't find any deals matching your criteria. Try adjusting the filters."); return
        self.ss.search_results, self.ss.search_results_index = results.to_dict('records'), 0
        self.add_message("assistant", f"Perfect! I've found **{len(self.ss.search_results)}** vehicles that match your criteria. Here is the first one:")
        self._handle_show_next_deal()

    def _handle_search_vehicle(self, params):
        self.ss.negotiation_context = None 
        make, model, year, color = params.get("make"), params.get("model"), params.get("year"), params.get("color")
        if make and not model and not year and not color:
            self.add_message("assistant", f"We have many {make} vehicles! To help me find the perfect one, could you please provide a bit more information? For example:")
            self.add_message("assistant", "• Are you interested in a specific **model**?\n• Do you have a preferred **year range**?\n• Any preference on **color** or **auction grade**?")
            return
        results = self.ss.inventory_df.copy()
        if make: results = results[results['make'] == make]
        if model: results = results[results['model'] == model]
        if year: results = results[results['year'] == year]
        if color: results = results[results['color'] == color]
        if results.empty: self.add_message("assistant", "Sorry, I couldn't find any vehicles matching your search."); return
        self.ss.search_results, self.ss.search_results_index = results.to_dict('records'), 0
        self.add_message("assistant", f"Great! I found **{len(self.ss.search_results)}** matching vehicles. Here's the best one:")
        self._handle_show_next_deal()

    def _handle_show_next_deal(self):
        results, idx = self.ss.search_results, self.ss.search_results_index
        if not results or idx >= len(results):
            self.add_message("assistant", "That's all the matching cars I have for now. Would you like to try a different search or adjust your filters?")
            self.ss.current_car_to_display = None; return
        self.ss.current_car_to_display, self.ss.search_results_index = results[idx], idx + 1

    def initiate_negotiation(self, car_data):
        self.ss.current_car_to_display = None
        original_price = car_data['price']
        self.ss.negotiation_context = {"car": car_data, "original_price": original_price, "floor_price": original_price * (1 - NEGOTIATION_MAX_DISCOUNT), "step": "initial", "last_agent_offer": None}
        self.add_message("assistant", f"Great choice! The listed price for the **{car_data['year']} {car_data['make']} {car_data['model']}** is **{self._format_price(original_price)}**. What would be your opening offer?")

    def _handle_discount_inquiry(self):
        if not self.ss.negotiation_context: self.add_message("assistant", "I can definitely look into discounts for you. Which car are you interested in?"); return
        ctx, price = self.ss.negotiation_context, self.ss.negotiation_context['original_price']
        opening_discount_price = int((price * 0.97) / 1000) * 1000
        self.add_message("assistant", f"I understand completely. For a serious buyer, I can start by offering a special price of **{self._format_price(opening_discount_price)}**. How does that sound as a starting point?")
        ctx.update({'last_agent_offer': opening_discount_price, 'step': 'countered'})

    def _handle_negotiation(self, offer_amount_base):
        if not self.ss.negotiation_context: return
        ctx = self.ss.negotiation_context
        price, floor_price = ctx['original_price'], ctx['floor_price']
        if ctx.get('last_agent_offer') and offer_amount_base >= ctx['last_agent_offer']:
             self.add_message("assistant", f"That's a fantastic offer! Let's make it official. I can accept **{self._format_price(offer_amount_base)}**. To confirm, just say 'I agree'."); ctx.update({'final_price': offer_amount_base, 'step': 'accepted'}); return
        if offer_amount_base >= price:
            self.add_message("assistant", f"That's the asking price, and I can certainly accept that! To confirm the deal at **{self._format_price(price)}**, just say 'I agree'."); ctx.update({'final_price': price, 'step': 'accepted'})
        elif offer_amount_base >= floor_price:
            counter_offer = int(((offer_amount_base + price) / 2) / 1000) * 1000
            if counter_offer >= price: counter_offer = int((price * 0.98)/1000) * 1000
            if counter_offer <= offer_amount_base: counter_offer = int((offer_amount_base * 1.02)/1000) * 1000
            self.add_message("assistant", f"Thank you, that's a strong offer. I have some flexibility and can meet you at **{self._format_price(counter_offer)}**. What do you think?"); ctx.update({'final_price': counter_offer, 'step': 'countered', 'last_agent_offer': counter_offer})
        else:
            self.add_message("assistant", f"I appreciate your offer. For this particular vehicle, the absolute best I can do is **{self._format_price(floor_price)}**. If that works for you, we have a deal."); ctx.update({'final_price': floor_price, 'step': 'countered', 'last_agent_offer': floor_price})

    def _handle_accept_offer(self):
        if not self.ss.negotiation_context: self.add_message("assistant", "Great! What are we making a deal on? Please select a car first."); return
        ctx, price_to_accept = self.ss.negotiation_context, self.ss.negotiation_context.get('final_price')
        if not price_to_accept and ctx.get('step') == 'initial': price_to_accept = ctx['original_price']
        if price_to_accept:
            car = ctx['car']; ctx['final_price'] = price_to_accept
            self.add_message("assistant", f"Excellent! Deal confirmed for the **{car['year']} {car['make']} {car['model']}** at **{self._format_price(price_to_accept)}**.")
            self.ss.invoice_to_render = ctx.copy()
            self.ss.last_deal_context, self.ss.negotiation_context, self.ss.query_context = ctx.copy(), None, {}
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
        # --- FIX: Re-architected UI flow for stability ---
        chat_container = st.container()
        with chat_container:
            render_chat_history(agent)

        card_placeholder = st.empty()
        if agent.ss.current_car_to_display:
            with card_placeholder.container():
                render_car_card(agent, agent.ss.current_car_to_display)
        
        invoice_placeholder = st.empty()
        if agent.ss.get("invoice_to_render"):
            with invoice_placeholder.container():
                render_invoice_button(agent, agent.ss.pop("invoice_to_render"))

        # Centralized action handling
        user_action = st.chat_input("Your message...")
        if agent.ss.get("button_action"):
            user_action = agent.ss.pop("button_action")
            
        if user_action:
            agent.respond(user_action)
            st.rerun()

    else: st.info(f"👋 Welcome! I'm {BOT_NAME}. Please fill out your profile and click 'Start Chat' to begin.")

def render_sidebar(agent):
    with st.sidebar:
        st.header("Lead Profile 📋")
        if not agent.ss.chat_started:
            if st.button("Start Chat", type="primary", use_container_width=True):
                agent.ss.chat_started, agent.ss.history, agent.ss.query_context = True, [], {}
                agent.add_message("assistant", f"Welcome! I'm {BOT_NAME}, your personal AI sales agent. How can I help?")
                st.rerun()
        st.markdown("---")
        st.info(agent.ss.data_source_name)
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
        filters['color'] = st.selectbox("Color", [""] + sorted(list(agent.ss.inventory_df['color'].unique())))
        filters['grade'] = st.selectbox("Auction Grade", [""] + sorted(list(agent.ss.inventory_df['grade'].unique())))
        st.markdown("---")
        if st.button("Apply Filters & Show Deals", use_container_width=True):
            st.session_state.button_action = "show deals"
            st.rerun()
        st.markdown("---")
        st.header("Chat History")
        if st.button("Download Transcript", use_container_width=True):
            transcript = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in agent.ss.history])
            st.download_button("Click to Download", transcript, "chat_transcript.txt", "text/plain")

def render_chat_history(agent):
    for msg in agent.ss.history:
        avatar = BOT_AVATAR_URL if msg['role'] == 'assistant' else USER_AVATAR_URL
        with st.chat_message(msg['role'], avatar=avatar):
            st.markdown(msg['content'])

def render_car_card(agent, car):
    with st.container(border=True):
        st.subheader(f"{car['year']} {car['make']} {car['model']}")
        c1, c2 = st.columns([1, 2])
        c1.image(car['image_url'], use_column_width=True)
        with c2:
            st.markdown(f"**Price:** {agent._format_price(car['price'])}")
            st.markdown(f"**Mileage:** {car['mileage']:,} km | **Fuel:** {car['fuel']}")
            st.markdown(f"**Transmission:** {car['transmission']} | **Color:** {car['color']}")
            st.markdown(f"**Auction Grade:** {car['grade']} | **Location:** {car['location']}")
        with st.expander("Show Market Comparison"):
            main_model, main_make, main_year = car['model'], car['make'], car['year']
            market_df = agent.ss.get("market_prices_df")
            market_data_source = []
            if market_df is not None:
                market_row = market_df[(market_df['make'] == main_make) & (market_df['model'] == main_model) & (market_df['year'] == main_year)]
                if not market_row.empty:
                    bf_price = market_row.iloc[0].get('beforward_price_jpy')
                    sbt_price = market_row.iloc[0].get('sbtjapan_price_jpy')
                    m_c1, m_c2 = st.columns(2)
                    m_c1.metric("BeForward.jp Price", agent._format_price(bf_price) if pd.notna(bf_price) else "N/A", delta_color="off")
                    m_c2.metric("SBTJapan.com Price", agent._format_price(sbt_price) if pd.notna(sbt_price) else "N/A", delta_color="off")
                    if pd.notna(bf_price): market_data_source.append({'date': datetime.now(), 'price': bf_price, 'source': 'BeForward.jp'})
                    if pd.notna(sbt_price): market_data_source.append({'date': datetime.now(), 'price': sbt_price, 'source': 'SBTJapan.com'})

            price_df, currency, rate = agent.ss.price_history_df, agent.ss.currency, CURRENCIES.get(agent.ss.currency, 1)
            history_data = price_df[(price_df['model'] == main_model) & (price_df['make'] == main_make) & (price_df['date'] >= pd.to_datetime(datetime.now()) - DateOffset(months=6))]
            history_data = history_data.copy(); history_data['display_price'] = history_data['avg_price'] * rate
            if not history_data.empty:
                chart = alt.Chart(history_data).mark_area(line={'color':'#4A90E2'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='white', offset=0), alt.GradientStop(color='#4A90E2', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X('date:T', title='Date', axis=alt.Axis(format="%b %Y")), y=alt.Y('display_price:Q', title=f'Avg. Price ({currency})', scale=alt.Scale(zero=False)), tooltip=[alt.Tooltip('date:T', format='%B %Y'), alt.Tooltip('display_price:Q', format=',.0f')]).properties(title=f'6-Month Price Trend for {main_make} {main_model}')
                if market_data_source:
                    market_df = pd.DataFrame(market_data_source)
                    market_df['display_price'] = market_df['price'] * rate
                    rule = alt.Chart(market_df).mark_rule(strokeDash=[5,5], size=2).encode(y='display_price:Q', color=alt.Color('source:N', legend=alt.Legend(title="Competitor Prices")))
                    chart = (chart + rule).interactive()
                st.altair_chart(chart, use_container_width=True)
            else: st.write("Not enough historical data to display a price trend for this model.")
        b_c1, b_c2 = st.columns(2)
        if b_c1.button("❤️ Like & Make Offer", key=f"offer_{car['id']}", use_container_width=True):
            agent.initiate_negotiation(car); st.rerun()
        if b_c2.button("❌ Pass (Next Car)", key=f"pass_{car['id']}", use_container_width=True):
            agent.respond("next car"); st.rerun()

def render_invoice_button(agent, context):
    if not ENABLE_PDF_INVOICING: st.error("PDF generation is disabled. Please ensure the 'fpdf' library is installed."); return
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
    st.download_button("📥 Download Invoice PDF", pdf_bytes, f"invoice_{car['id']}.pdf", "application/pdf", key=f"download_{car['id']}")

# ======================================================================================
# 4. Main App Execution
# ======================================================================================

if __name__ == "__main__":
    render_ui()

# End of script
