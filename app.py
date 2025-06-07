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
MAX_QUERY_LENGTH = 200
MAX_SUGGESTIONS = 5
BOT_AVATAR_URL = "https://otoz.ai/assets/bot-avatar.png"
USER_AVATAR_URL = None

# 1. Page setup
st.set_page_config(
    page_title="Otoz.ai Sales Assistant",
    page_icon="🚗",
    layout="wide"
)
st.title("Otoz.ai Inventory-Aware Sales Chatbot")

# 2. Sidebar for lead capture & filters
with st.sidebar:
    st.header("Lead Profile 📋")
    st.session_state.user_name = st.text_input("Name", st.session_state.get("user_name", ""))
    budget = st.slider("Budget (PKR)", 500_000, 5_000_000, (1_000_000, 2_000_000))
    timeline = st.radio("Purchase Timeline", ["Immediately","1-3 months","3-6 months","Later"])
    st.markdown("---")
    st.header("Filters 🔎")
    filter_make = st.selectbox("Make", [""] + DUMMY_MAKES)
    filter_year = st.slider("Year Range", 2015, 2025, (2018, 2022))
    st.markdown("---")
    st.markdown("Need help? [Contact us](mailto:inquiry@otoz.ai)")

# 3. Session state initialization
if "history" not in st.session_state:
    st.session_state.history = []
if "negotiation" not in st.session_state:
    st.session_state.negotiation = None
if "dummy_inventory" not in st.session_state:
    dummy = []
    for _ in range(1000):
        mk = random.choice(DUMMY_MAKES)
        model = random.choice(DUMMY_MODELS[mk])
        yr = random.randint(2015, 2025)
        price = random.randint(500_000, 5_000_000)
        loc = random.choice(["Karachi","Lahore","Islamabad"])
        img_url = f"https://dummyimage.com/200x100/000/fff&text={mk}+{yr}"
        dummy.append({"year":yr,"make":mk,"model":model,"price":price,"location":loc,"image_url":img_url})
    st.session_state.dummy_inventory = dummy

# 4. Inventory fetch helper
@st.cache_data
def fetch_inventory(make: str, year: int):
    # Try CSV first
    try:
        with st.spinner("Fetching inventory..."):
            resp = requests.get(CSV_URL, timeout=5)
            resp.raise_for_status()
            text = resp.text
            reader = csv.DictReader(io.StringIO(text))
            results = []
            for row in reader:
                try:
                    ry = int(row.get("year",0))
                except ValueError:
                    continue
                if ry == year and row.get("make","").strip().lower() == make.lower():
                    price = int(row.get("price",0)) if row.get("price","").isdigit() else None
                    results.append({
                        "year":ry,
                        "make":row.get("make",""),
                        "model":row.get("model",""),
                        "price":price,
                        "location":row.get("location",""),
                        "image_url":row.get("image_url",
                                         f"https://dummyimage.com/200x100/000/fff&text={make}+{year}")
                    })
            if results:
                return results
    except Exception:
        pass
    # Fallback to dummy
    return [car for car in st.session_state.dummy_inventory if car['make'].lower()==make.lower() and car['year']==year]

# 5. Initial greeting
if not st.session_state.history:
    st.session_state.history.append({"role":"assistant","content":
        "👋 Hi! Welcome to Otoz.ai Sales. What’s your name?"
    })

# 6. Chat input
user_input = st.chat_input("Enter your message...")
col1, col2 = st.columns(2)
if col1.button("Show Deals"): user_input = "show deals"
if col2.button("Contact Sales"): user_input = "contact support"

# 7. Process input
if user_input:
    st.session_state.history.append({"role":"user","content":user_input})
    text = user_input.strip()
    lc = text.lower()
    processed = False

    # Collect name
    if st.session_state.history and "What’s your name?" in st.session_state.history[0]['content'] and len(st.session_state.history)==1:
        st.session_state.user_name = text
        st.session_state.history.append({"role":"assistant","content":
            f"Nice to meet you, {text}! Please tell me the make and year you are interested in (e.g., Honda 2020)."
        })
        processed = True

    # Show Deals shortcut
    if not processed and lc == "show deals":
        st.session_state.history.append({"role":"assistant","content":
            "Sure! Which make and year (e.g., Toyota 2018) are you looking for?"
        })
        processed = True

    # Inventory lookup & negotiation start
    if not processed:
        m = re.match(r"(\w+)\s*(\d{4})", text)
        if m and m.group(1).capitalize() in DUMMY_MAKES:
            make = m.group(1).capitalize()
            year = int(m.group(2))
            st.session_state.history.append({"role":"assistant","content":
                f"Looking up {make} {year} for you..."
            })
            cars = fetch_inventory(make, year)
            if cars:
                car = cars[0]
                # price trend chart
                records = st.session_state.dummy_inventory
                years = sorted({c['year'] for c in records if c['make']==make})
                avg = {y: int(sum(c['price'] for c in records if c['make']==make and c['year']==y)/max(1,len([c for c in records if c['make']==make and c['year']==y]))) for y in years}
                st.line_chart(avg, use_container_width=True)
                # display card
                st.image(car['image_url'], width=200)
                st.markdown(f"**{car['year']} {car['make']} {car['model']}**")
                st.markdown(f"Price: PKR {int(car['price']):,}")
                st.markdown(f"Location: {car['location']}")
                # start negotiation
                st.session_state.negotiation = {'price':car['price'],'step':1,'car':car}
                st.session_state.history.append({"role":"assistant","content":
                    f"This {make} {year} is listed at PKR {car['price']:,}. What would you like to offer?"
                })
            else:
                st.session_state.history.append({"role":"assistant","content":
                    "I’m sorry, we have no listings for that model. Email inquiry@otoz.ai for help."
                })
            processed = True

    # Negotiation steps
    if not processed and st.session_state.negotiation:
        neg = st.session_state.negotiation
        offer = None
        try: offer = int(re.sub(r"\D","",text))
        except: pass
        if neg['step']==1 and offer:
            counter = int(neg['price']*0.95)
            neg['step']=2
            st.session_state.history.append({"role":"assistant","content":
                f"Thanks for PKR {offer:,}. Can I offer PKR {counter:,}?"
            })
        elif neg['step']==2 and offer and ('yes' in lc or offer>=counter):
            final = int(neg['price']*0.90)
            neg['step']=3
            st.session_state.history.append({"role":"assistant","content":
                f"Great! Final price PKR {final:,}. Shall I prepare the invoice?"
            })
        elif neg['step']==3 and ('yes' in lc):
            inv = FPDF(); inv.add_page(); inv.set_font("Arial","B",16)
            inv.cell(0,10,"Otoz.ai Invoice",ln=1,align='C')
            inv.ln(5); inv.set_font("Arial",size=12)
            car = neg['car']; final = int(car['price']*0.90)
            inv.multi_cell(0,8,
                f"Customer: {st.session_state.user_name}\n"
                f"Car: {car['year']} {car['make']} {car['model']}\n"
                f"Price: PKR {final:,}\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d')}"
            )
            pdf_bytes = inv.output(dest='S').encode('latin-1')
            st.session_state.history.append({"role":"assistant","content":"Here is your invoice:"})
            st.download_button("Download PDF Invoice", pdf_bytes, "invoice.pdf","application/pdf")
            st.session_state.negotiation=None
        processed=True

    # Fallback
    if not processed:
        st.session_state.history.append({"role":"assistant","content":
            "For further assistance, contact inquiry@otoz.ai or visit otoz.ai/help."
        })

# 8. Render chat history
for msg in st.session_state.history:
    avatar = BOT_AVATAR_URL if msg['role']=='assistant' else USER_AVATAR_URL
    with st.chat_message(msg['role'], avatar=avatar): st.write(msg['content'])

# 9. Export transcript
if st.button("Download Chat Transcript"):
    txt = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.history])
    st.download_button("Download Transcript", txt, "chat.txt","text/plain")

# End of script
