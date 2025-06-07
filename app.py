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
    # ... other makes
}
MIN_QUERY_LENGTH = 3
MAX_SUGGESTIONS = 5
BOT_AVATAR_URL = "https://otoz.ai/assets/bot-avatar.png"
USER_AVATAR_URL = None
CURRENCIES = {"PKR":1, "USD":1/280, "JPY":1/2.0}
# ─────────────────────────────────────────────────────────────────────────────

# 1. Page config and theme
st.set_page_config(
    page_title="Otoz.ai Sales Assistant",
    page_icon="🚗",
    layout="wide"
)
st.title("Otoz.ai Inventory-Aware Sales Chatbot")

# 2. Sidebar: Profile, Filters, and Currency
with st.sidebar:
    st.header("Lead Profile 📋")
    if st.button("Start Chat"):
        st.session_state.started = True
    if st.session_state.get("started"):
        name = st.text_input("Name", st.session_state.get("user_name", ""))
        email = st.text_input("Email", st.session_state.get("user_email", ""))
        country = st.text_input("Country", st.session_state.get("user_country", ""))
        budget = st.slider("Budget (PKR)", 500_000, 5_000_000,
                           st.session_state.get("budget", (1_000_000,2_000_000)))
        currency = st.selectbox("Display Prices in", list(CURRENCIES.keys()),
                                st.session_state.get("currency","PKR"))
        if st.button("Save Profile"):
            st.session_state.user_name = name
            st.session_state.user_email = email
            st.session_state.user_country = country
            st.session_state.budget = budget
            st.session_state.currency = currency
            st.success("Profile saved!")
        st.markdown("---")
        st.header("Filters 🔎")
        st.selectbox("Make", [""]+DUMMY_MAKES, key="filter_make")
        st.slider("Year Range", 2015, 2025,
                  st.session_state.get("filter_year", (2018,2022)), key="filter_year")
        st.markdown("---")
        st.info("Click 'Show Deals' in chat to view featured offers.")

# 3. Session init
st.session_state.setdefault("history", [])
st.session_state.setdefault("negotiation", None)
if "dummy_inventory" not in st.session_state:
    inv = []
    for _ in range(500):
        mk = random.choice(DUMMY_MAKES)
        model = random.choice(DUMMY_MODELS.get(mk, []))
        yr = random.randint(2015, 2025)
        price = random.randint(500_000, 5_000_000)
        loc = random.choice(["Karachi","Lahore","Islamabad"])
        img = f"https://dummyimage.com/200x100/000/fff&text={mk}+{yr}"
        inv.append({"year":yr,"make":mk,"model":model,
                    "price":price,"location":loc,"image_url":img})
    st.session_state.dummy_inventory = inv

# 4. Helper: fetch inventory
@st.cache_data
def fetch_inventory(make, year):
    try:
        resp = requests.get(CSV_URL, timeout=5); resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = [r for r in reader if int(r["year"])==year and r["make"].lower()==make.lower()]
        if rows: return rows
    except:
        pass
    return [c for c in st.session_state.dummy_inventory if c['make'].lower()==make.lower() and c['year']==year]

# 5. Initial greeting
if not st.session_state.history:
    st.session_state.history.append({"role":"assistant",
        "content":"👋 Welcome! Save your profile on the left, then 'Show Deals' or ask (e.g., Honda 2020)."
    })

# 6. Chat input & quick actions
user_input = st.chat_input("Your message...")
col1, col2 = st.columns(2)
if col1.button("Show Deals"): user_input = "show deals"
if col2.button("Contact Sales"): user_input = "contact support"

# 7. Process chat
if user_input:
    st.session_state.history.append({"role":"user","content":user_input})
    lc = user_input.lower(); done=False
    # Show Deals
    if lc=="show deals":
        st.session_state.history.append({"role":"assistant",
            "content":"Featured deals for you:"})
        # Use profile filters
        mk=st.session_state.get("filter_make","")
        yrmin,yrmax=st.session_state.get("filter_year",(2018,2022))
        notes=[]
        for c in st.session_state.dummy_inventory:
            if (not mk or c['make']==mk) and yrmin<=c['year']<=yrmax:
                notes.append(c)
        sample=random.sample(notes, min(3,len(notes)))
        for car in sample:
            price_conv=int(car['price']*CURRENCIES.get(st.session_state.get("currency","PKR"),1))
            st.session_state.history.append({"role":"assistant",
                "content":f"{car['make']} {car['model']} ({car['year']}) - {st.session_state.get('currency')} {price_conv:,}"})
        done=True
    # Contact
    if not done and lc=="contact support":
        st.session_state.history.append({"role":"assistant",
            "content":"Email inquiry@otoz.ai or call +123456789."})
        done=True
    # Lookup
    if not done:
        m=re.match(r"(\w+)\s*(\d{4})", user_input)
        if m and m.group(1).capitalize() in DUMMY_MAKES:
            make=m.group(1).capitalize(); year=int(m.group(2))
            st.session_state.history.append({"role":"assistant",
                "content":f"Looking for {make} {year}..."})
            cars=fetch_inventory(make,year)
            # Chart
            recs=st.session_state.dummy_inventory
            yrs=sorted({c['year'] for c in recs if c['make']==make})
            avg={y:sum(c['price'] for c in recs if c['make']==make and c['year']==y)/max(1,len([c for c in recs if c['make']==make and c['year']==y])) for y in yrs}
            st.line_chart(avg)
            # card + negotiation
            car=cars[0]
            price_conv=int(car['price']*CURRENCIES.get(st.session_state.get('currency','PKR'),1))
            st.image(car['image_url'],width=200)
            st.write(f"**{car['year']} {car['make']} {car['model']}**")
            st.write(f"Price: {st.session_state.get('currency','PKR')} {price_conv:,}")
            st.write(f"Location: {car['location']}")
            st.session_state.negotiation={'price':car['price'],'step':1,'car':car}
            st.session_state.history.append({"role":"assistant",
                "content":f"Listed at {st.session_state.get('currency','PKR')} {price_conv:,}. Your offer?"})
            done=True
    # Negotiation
    if not done and st.session_state.negotiation:
        neg=st.session_state.negotiation; offer=None
        try: offer=int(re.sub(r"\D","",user_input))
        except: pass
        if neg['step']==1 and offer:
            cnt=int(neg['price']*0.95)
            neg['step']=2
            st.session_state.history.append({"role":"assistant",
                "content":f"Can I do PKR {cnt:,}?"})
        elif neg['step']==2 and (offer>=cnt or 'yes' in lc):
            final=int(neg['price']*0.90); neg['step']=3
            st.session_state.history.append({"role":"assistant",
                "content":f"Final price PKR {final:,}. Deal?"})
        elif neg['step']==3 and 'yes' in lc:
            if ENABLE_PDF:
                pdf=FPDF();pdf.add_page();pdf.set_font("Arial","B",16)
                pdf.cell(0,10,"Otoz.ai Invoice",ln=1,align='C');pdf.ln(5)
                pdf.set_font("Arial",size=12)
                car=neg['car'];fp=int(car['price']*0.90)
                pdf.multi_cell(0,8,f"Customer: {st.session_state.user_name}\nCar: {car['year']} {car['make']} {car['model']}\nPrice: PKR {fp:,}\nDate: {datetime.now().strftime('%Y-%m-%d')}")
                data=pdf.output(dest='S').encode('latin-1')
                st.session_state.history.append({"role":"assistant","content":"Invoice:"})
                st.download_button("Download PDF",data,"invoice.pdf","application/pdf")
            else:
                st.session_state.history.append({"role":"assistant","content":"Install 'fpdf' to enable invoices."})
            st.session_state.negotiation=None;done=True
    # Fallback
    if not done:
        st.session_state.history.append({"role":"assistant",
            "content":"Try 'Show Deals' or specify make and year (e.g., Toyota 2019)."})

# 8. Render history
for msg in st.session_state.history:
    avatar=BOT_AVATAR_URL if msg['role']=='assistant' else USER_AVATAR_URL
    with st.chat_message(msg['role'],avatar=avatar): st.write(msg['content'])

# 9. Transcript
if st.button("Download Chat Transcript"):
    txt="\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.history])
    st.download_button("Download Transcript",txt,"chat.txt","text/plain")

# End of script
