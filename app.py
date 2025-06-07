import os
import re
import csv
import io
import random
import requests
import streamlit as st
from datetime import datetime
from fpdf import FPDF

# ─────────────────────────────────────────────────────────────────────────────
# Constants
CSV_URL           = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)
CSV_COLUMNS       = ["year", "make", "model", "price", "location", "image_url"]
DUMMY_MAKES       = ["Toyota","Honda","Nissan","Suzuki","Mazda","Subaru","Mitsubishi","Lexus"]
DUMMY_MODELS      = {  # expanded models dict with image placeholders
    "Toyota": ["Corolla","Camry","RAV4","Prius","Yaris","Hilux","Fortuner","Land Cruiser"],
    "Honda": ["Civic","Accord","CR-V","Fit","Jazz","HR-V","Odyssey","Pilot"],
    "Nissan": ["Altima","Sentra","Rogue","Leaf","X-Trail","Murano","Skyline"],
    "Suzuki": ["Swift","Vitara","Ciaz","Ignis","Jimny","Alto"],
    "Mazda": ["Mazda3","Mazda6","CX-5","MX-5","CX-9"],
    "Subaru": ["Impreza","Forester","Outback","XV","WRX"],
    "Mitsubishi": ["Lancer","Outlander","Mirage","Pajero"],
    "Lexus": ["IS","ES","RX","NX","LC"]
}
MIN_QUERY_LENGTH  = 3
MAX_QUERY_LENGTH  = 200
MAX_SUGGESTIONS   = 5
BOT_AVATAR_URL    = "https://otoz.ai/assets/bot-avatar.png"
USER_AVATAR_URL   = None
# ─────────────────────────────────────────────────────────────────────────────

# 1. Page and theme setup
st.set_page_config(
    page_title="Otoz.ai Sales Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Sidebar: Lead capture & filters & summary
with st.sidebar:
    st.header("Your Profile 📋")
    name = st.text_input("Name", st.session_state.get("user_name", ""))
    budget = st.slider("Budget (PKR)", 500_000, 5_000_000, (1_000_000, 2_000_000))
    urgency = st.radio("Purchase Timeline", ["Immediately", "1-3 months", "3-6 months", "Later"])
    st.markdown("---")
    st.header("Filters 🔎")
    filter_make = st.selectbox("Make", [""] + DUMMY_MAKES)
    filter_year = st.slider("Year Range", 2015, 2025, (2018, 2022))
    st.markdown("---")
    st.markdown("Need help? [Contact us](mailto:inquiry@otoz.ai)")

# Store name if entered
if name and st.session_state.get("user_name") != name:
    st.session_state.user_name = name

# 3. Session init
if "history" not in st.session_state:
    st.session_state.history = []
if "negotiation" not in st.session_state:
    st.session_state.negotiation = None
if "dummy_inventory" not in st.session_state:
    dummy = []
    for _ in range(1000):
        mk = random.choice(DUMMY_MAKES)
        model = random.choice(DUMMY_MODELS.get(mk, []))
        yr = random.randint(2015, 2025)
        price = random.randint(500_000, 5_000_000)
        loc = random.choice(["Karachi","Lahore","Islamabad"])
        img = f"https://dummyimage.com/200x100/000/fff&text={mk}+{yr}"
        dummy.append({"year": yr, "make": mk, "model": model,
                      "price": price, "location": loc, "image_url": img})
    st.session_state.dummy_inventory = dummy

# Helper: fetch inventory
@st.cache_data
def fetch_inventory(make: str, year: int):
    try:
        with st.spinner("Loading inventory..."):
            resp = requests.get(CSV_URL, timeout=5); resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            results = [row for row in reader if int(row.get("year",0))==year and row.get("make","\").lower()==make.lower()]
            if results: return results
    except:
        pass
    return [car for car in st.session_state.dummy_inventory if car['make'].lower()==make.lower() and car['year']==year]

# 4. Initial greeting
if not st.session_state.history:
    st.session_state.history.append({"role":"assistant","content":
        "👋 Hi! Welcome to Otoz.ai. I’m your car sales assistant. May I have your name?"
    })

# 5. Chat input & quick replies
user_input = st.chat_input("Type your message or pick an option…")
col1, col2 = st.columns(2)
if col1.button("Show Deals"): user_input = "Show me deals"
if col2.button("Contact Sales"): user_input = "Contact support"

# 6. Process message
if user_input:
    st.session_state.history.append({"role":"user","content":user_input})
    processed = False
    text = user_input.strip(); lc = text.lower()

    # 6A. Show deals (quick flow)
    if lc == "show me deals":
        st.session_state.history.append({"role":"assistant","content":
            f"Sure {st.session_state.user_name or ''}, please specify make and year (e.g., Honda 2020)."
        })
        processed = True

    # 6B. Inventory lookup and start negotiation
    if not processed and re.match(r"(\w+).*?(\d{4})", text):
        m = re.match(r"(\w+).*?(\d{4})", text)
        make = m.group(1).capitalize(); year = int(m.group(2))
        st.session_state.history.append({"role":"assistant","content":
            f"Looking for {make} {year}..."
        })
        cars = fetch_inventory(make, year)
        if cars:
            car = cars[0]
            # Price trend chart
            years = sorted({c['year'] for c in st.session_state.dummy_inventory if c['make']==make})
            avg = {y: sum(c['price'] for c in st.session_state.dummy_inventory if c['make']==make and c['year']==y)/len([c for c in st.session_state.dummy_inventory if c['make']==make and c['year']==y]) for y in years}
            st.line_chart(avg, use_container_width=True)
            # Show car card
            st.image(car['image_url'], width=200)
            st.markdown(f"**{car['year']} {car['make']} {car['model']}**")
            st.markdown(f"Price: PKR {int(car['price']):,}")
            st.markdown(f"Location: {car['location']}")
            # Initiate negotiation
            st.session_state.negotiation = {'price': car['price'], 'step':1, 'details':car}
            st.session_state.history.append({"role":"assistant","content":
                f"This one is listed at PKR {car['price']:,}. What is your offer?"
            })
        else:
            st.session_state.history.append({"role":"assistant","content":
                "I’m sorry, we don’t have that exact model right now. Email inquiry@otoz.ai for assistance."
            })
        processed = True

    # 6C. Handle negotiation steps
    if not processed and st.session_state.negotiation:
        neg = st.session_state.negotiation
        offer = None
        try:
            offer = int(re.sub(r"\D", "", text))
        except:
            pass
        if neg['step']==1 and offer:
            counter = int(neg['price'] * 0.95)
            neg['step']=2
            st.session_state.history.append({"role":"assistant","content":
                f"Thank you for PKR {offer:,}. Can we do PKR {counter:,}?"
            })
        elif neg['step']==2 and (offer==counter or 'yes' in lc):
            final = int(neg['price'] * 0.90)
            neg['step']=3
            st.session_state.history.append({"role":"assistant","content":
                f"Great! Final offer: PKR {final:,}. Shall I prepare the invoice?"
            })
        elif neg['step']==3 and ('yes' in lc or offer==final):
            # Generate PDF invoice
            inv = FPDF()
            inv.add_page(); inv.set_font("Arial","B",16)
            inv.cell(0,10,"Otoz.ai Invoice",ln=1,align='C')
            inv.ln(5); inv.set_font("Arial",size=12)
            car = neg['details']
            inv.multi_cell(0,8,
                f"Customer: {st.session_state.user_name}\n"
                f"Car: {car['year']} {car['make']} {car['model']}\n"
                f"Price: PKR {final:,}\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d')}"
            )
            pdf_data = inv.output(dest='S').encode('latin-1')
            st.session_state.history.append({"role":"assistant","content":
                "Here is your invoice:"})
            st.download_button("Download Invoice", pdf_data, "invoice.pdf", "application/pdf")
            st.session_state.negotiation=None
        processed=True

    # 6D. Fallback
    if not processed:
        st.session_state.history.append({"role":"assistant","content":
            "For more info, email inquiry@otoz.ai or visit otoz.ai/help."
        })

# 7. Display history & transcript export
for msg in st.session_state.history:
    avatar = BOT_AVATAR_URL if msg['role']=='assistant' else USER_AVATAR_URL
    with st.chat_message(msg['role'], avatar=avatar): st.write(msg['content'])

if st.button("Download Chat Transcript"):
    transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.history])
    st.download_button("Download TXT", transcript, "chat.txt")

# End of script
