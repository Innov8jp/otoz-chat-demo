import os
import re
import csv
import io
import random
import requests
import streamlit as st
from datetime import datetime
try:
    from fpdf import FPDF
    ENABLE_PDF = True
except ImportError:
    ENABLE_PDF = False

# ─────────────────────────────────────────────────────────────────────────────
# Constants
CSV_URL = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)
DUMMY_MAKES = ["Toyota","Honda","Nissan","Suzuki","Mazda","Subaru","Mitsubishi","Lexus"]
DUMMY_MODELS = {
    "Toyota": ["Corolla","Camry","RAV4","Prius","Yaris","Hilux","Fortuner","Land Cruiser"],
    "Honda": ["Civic","Accord","CR-V","Fit","Jazz","HR-V","Odyssey","Pilot"],
    "Nissan": ["Altima","Sentra","Rogue","Leaf","X-Trail","Murano","Skyline"],
    "Suzuki": ["Swift","Vitara","Ciaz","Ignis","Jimny","Alto"],
    "Mazda": ["Mazda3","Mazda6","CX-5","MX-5","CX-9"],
    "Subaru": ["Impreza","Forester","Outback","XV","WRX"],
    "Mitsubishi": ["Lancer","Outlander","Mirage","Pajero"],
    "Lexus": ["IS","ES","RX","NX","LC"]
}
MIN_QUERY_LENGTH = 3
MAX_SUGGESTIONS = 5
BOT_AVATAR_URL = "https://otoz.ai/assets/bot-avatar.png"
USER_AVATAR_URL = None

# 1. Streamlit page config
st.set_page_config(
    page_title="Otoz.ai Sales Assistant",
    page_icon="🚗",
    layout="wide"
)
st.title("Otoz.ai Inventory-Aware Sales Chatbot")

# 2. Sidebar: Onboarding and Quick Deals
with st.sidebar:
    st.header("Welcome to Otoz.ai")
    contacted = st.session_state.get("contacted", False)
    if not contacted:
        if st.button("Start Chat"):
            st.session_state.contacted = True
            contacted = True
    if contacted:
        st.subheader("Your Details 📋")
        st.session_state.user_name = st.text_input("Name", st.session_state.get("user_name", ""))
        st.session_state.user_email = st.text_input("Email", st.session_state.get("user_email", ""))
        st.session_state.user_country = st.text_input("Country", st.session_state.get("user_country", ""))
        st.markdown("---")
        st.subheader("Featured Deals 🔥")
        deals = random.sample(
            [f"{mk} {random.choice(DUMMY_MODELS[mk])} ({yr}) - PKR {random.randint(500000,2000000):,}" \
             for mk in DUMMY_MAKES for yr in range(2018, 2023)],
            3
        )
        for d in deals:
            st.write(d)
        st.markdown("---")
        st.info("Use the 'Show Deals' button in chat to view these offers here.")

# 3. Session state initialization
if "history" not in st.session_state:
    st.session_state.history = []
if "negotiation" not in st.session_state:
    st.session_state.negotiation = None
if "dummy_inventory" not in st.session_state:
    dummy = []
    for _ in range(500):
        mk = random.choice(DUMMY_MAKES)
        model = random.choice(DUMMY_MODELS[mk])
        yr = random.randint(2015, 2025)
        price = random.randint(500_000, 5_000_000)
        loc = random.choice(["Karachi","Lahore","Islamabad"])
        img = f"https://dummyimage.com/200x100/000/fff&text={mk}+{yr}"
        dummy.append({"year": yr, "make": mk, "model": model, "price": price, "location": loc, "image_url": img})
    st.session_state.dummy_inventory = dummy

# 4. Inventory fetch helper
@st.cache_data
def fetch_inventory(make: str, year: int):
    try:
        with st.spinner("Fetching inventory..."):
            resp = requests.get(CSV_URL, timeout=5)
            resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            results = []
            for row in reader:
                try:
                    ry = int(row.get("year", 0))
                except ValueError:
                    continue
                if ry == year and row.get("make", "").strip().lower() == make.lower():
                    price = int(row.get("price", 0)) if row.get("price", "").isdigit() else None
                    results.append({
                        "year": ry,
                        "make": row.get("make", ""),
                        "model": row.get("model", ""),
                        "price": price,
                        "location": row.get("location", ""),
                        "image_url": row.get(
                            "image_url",
                            f"https://dummyimage.com/200x100/000/fff&text={make}+{year}"
                        )
                    })
            if results:
                return results
    except Exception:
        pass
    # Fallback to dummy
    return [c for c in st.session_state.dummy_inventory if c['make'].lower() == make.lower() and c['year'] == year]

# 5. Initial greeting
if not st.session_state.history:
    st.session_state.history.append({
        "role": "assistant",
        "content": "👋 Hello! I’m Otoz.ai’s sales assistant. Click 'Show Deals' or type a request (e.g., Honda 2020)."
    })

# 6. Chat input with quick actions
user_input = st.chat_input("Your message...")
col1, col2 = st.columns(2)
if col1.button("Show Deals"): user_input = "show deals"
if col2.button("Contact Sales"): user_input = "contact support"

# 7. Process chat messages
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})
    lc = user_input.lower()
    processed = False

    # 7A. Show Deals
    if lc == "show deals":
        st.session_state.history.append({
            "role": "assistant",
            "content": "Here are featured deals based on your budget and preferences:" 
        })
        # Repeat sidebar deals
        deals = random.sample(
            [f"{mk} {random.choice(DUMMY_MODELS[mk])} ({yr}) - PKR {random.randint(500000,2000000):,}" \
             for mk in DUMMY_MAKES for yr in range(2018, 2023)],
            3
        )
        for d in deals:
            st.session_state.history.append({"role": "assistant", "content": d})
        processed = True

    # 7B. Contact Sales
    if not processed and lc == "contact support":
        st.session_state.history.append({
            "role": "assistant",
            "content": "You can reach our sales team at inquiry@otoz.ai or call +123456789."
        })
        processed = True

    # 7C. Inventory lookup & negotiation start
    if not processed:
        m = re.match(r"(\w+)\s*(\d{4})", user_input)
        if m and m.group(1).capitalize() in DUMMY_MAKES:
            make = m.group(1).capitalize()
            year = int(m.group(2))
            st.session_state.history.append({
                "role": "assistant",
                "content": f"Looking up {make} {year}..."
            })
            cars = fetch_inventory(make, year)
            # Price trend chart
            recs = st.session_state.dummy_inventory
            yrs = sorted({c['year'] for c in recs if c['make'] == make})
            avg_prices = {y: int(
                sum(c['price'] for c in recs if c['make'] == make and c['year'] == y) /
                max(1, len([c for c in recs if c['make'] == make and c['year'] == y]))
            ) for y in yrs}
            st.line_chart(avg_prices, use_container_width=True)
            # Display first car card
            car = cars[0]
            st.image(car['image_url'], width=200)
            st.markdown(f"### {car['year']} {car['make']} {car['model']}")
            st.write(f"**Price:** PKR {car['price']:,}")
            st.write(f"**Location:** {car['location']}")
            # Begin negotiation
            st.session_state.negotiation = {"price": car['price'], "step": 1, "car": car}
            st.session_state.history.append({
                "role": "assistant",
                "content": f"This one is PKR {car['price']:,}. What's your offer?"
            })
            processed = True

    # 7D. Negotiation flow
    if not processed and st.session_state.negotiation:
        neg = st.session_state.negotiation
        offer = None
        try:
            offer = int(re.sub(r"\D", "", user_input))
        except:
            pass
        if neg['step'] == 1 and offer:
            counter = int(neg['price'] * 0.95)
            neg['step'] = 2
            st.session_state.history.append({
                "role": "assistant",
                "content": f"Thank you for PKR {offer:,}. Can I offer PKR {counter:,}?"
            })
        elif neg['step'] == 2 and (offer >= counter or 'yes' in lc):
            final_price = int(neg['price'] * 0.90)
            neg['step'] = 3
            st.session_state.history.append({
                "role": "assistant",
                "content": f"Great! Final price PKR {final_price:,}. Shall I draft the invoice?"
            })
        elif neg['step'] == 3 and 'yes' in lc:
            if ENABLE_PDF:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "Otoz.ai Invoice", ln=1, align='C')
                pdf.ln(5)
                pdf.set_font("Arial", size=12)
                car = neg['car']
                final_price = int(car['price'] * 0.90)
                pdf.multi_cell(0, 8,
                    f"Customer: {st.session_state.user_name}\n"
                    f"Car: {car['year']} {car['make']} {car['model']}\n"
                    f"Price: PKR {final_price:,}\n"
                    f"Date: {datetime.now().strftime('%Y-%m-%d')}"
                )
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.session_state.history.append({
                    "role": "assistant",
                    "content": "Here is your invoice:"})
                st.download_button("Download Invoice", pdf_bytes, "invoice.pdf", "application/pdf")
            else:
                st.session_state.history.append({
                    "role": "assistant",
                    "content": "Invoice feature unavailable. Install 'fpdf' to enable."
                })
            st.session_state.negotiation = None
        processed = True

    # 7E. Fallback for unprocessed
    if not processed:
        st.session_state.history.append({
            "role": "assistant",
            "content": "Sorry, I didn't catch that. Try 'Show Deals' or specify a model and year (e.g. Honda 2020)."
        })

# 8. Render chat history
for msg in st.session_state.history:
    avatar = BOT_AVATAR_URL if msg['role'] == 'assistant' else USER_AVATAR_URL
    with st.chat_message(msg['role'], avatar=avatar):
        st.write(msg['content'])

# 9. Download transcript
if st.button("Download Chat Transcript"):
    transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.history])
    st.download_button("Download Transcript", transcript, "chat.txt", "text/plain")

# End of script
