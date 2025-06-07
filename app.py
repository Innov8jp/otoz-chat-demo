import os
import re
import csv
import io
import requests
import streamlit as st
from openai import OpenAI, OpenAIError

# ─────────────────────────────────────────────────────────────────────────────
# Constants
CSV_URL           = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)
CSV_COLUMNS       = ["year", "make", "model", "price", "location"]
DEFAULT_MODEL     = "gpt-4o-mini"
MIN_QUERY_LENGTH  = 3
MAX_QUERY_LENGTH  = 200
MAX_HISTORY_TURNS = 10
MAX_SUGGESTIONS   = 5
# ─────────────────────────────────────────────────────────────────────────────

# 1. Validate OpenAI key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or not api_key.strip():
    st.error("Error: OPENAI_API_KEY not set.")
    st.stop()

# 2. Init OpenAI
try:
    client = OpenAI(api_key=api_key)
except OpenAIError as e:
    st.error(f"OpenAI init error: {e}")
    st.stop()

# 3. Page setup
st.set_page_config(page_title="Otoz.ai Chat", layout="wide")
st.title("Otoz.ai Inventory-Aware Chatbot")

# 4. History
if "history" not in st.session_state:
    st.session_state.history = []

# 5. Parse make/year
def parse_query(text: str) -> dict:
    info = {}
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m: info["year"] = int(m.group())
    for mk in ["Honda","Toyota","BMW","Suzuki","Nissan","Mercedes"]:
        if mk.lower() in text.lower():
            info["make"] = mk
            break
    return info

# 6. Fetch CSV inventory
def fetch_inventory(make: str, year: int) -> list:
    try:
        r = requests.get(CSV_URL, timeout=5)
        r.raise_for_status()
        data = r.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(data))
        results = []
        for row in reader:
            try:
                ry = int(row.get("year",0))
            except:
                continue
            if ry == year and row.get("make","").strip().lower() == make.lower():
                item = {c: row.get(c,"").strip() for c in CSV_COLUMNS}
                try: item["price"] = int(item["price"])
                except: pass
                results.append(item)
        return results
    except:
        return []

# 7. Display history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 8. Single‐hit chat input
user_input = st.chat_input("Ask me about our cars …")
if user_input:
    txt = user_input.strip()
    if len(txt) < MIN_QUERY_LENGTH:
        st.warning(f"Enter at least {MIN_QUERY_LENGTH} characters.")
        st.stop()
    if len(txt) > MAX_QUERY_LENGTH:
        st.warning(f"Max {MAX_QUERY_LENGTH} characters.")
        st.stop()

    st.session_state.history.append({"role":"user","content":txt})
    lc = txt.lower()

    # Count-style questions
    m = re.match(r"how many cars of (\w+).*?(\d{4})", lc)
    if m:
        mk, yr = m.group(1).capitalize(), int(m.group(2))
        cars = fetch_inventory(mk, yr)
        reply = f"We have {len(cars)} {mk} cars from {yr}."
        st.session_state.history.append({"role":"assistant","content":reply})
        st.stop()

    # Max-suggestion
    if "most number" in lc or "max suggestions" in lc:
        reply = f"I can suggest up to {MAX_SUGGESTIONS} cars."
        st.session_state.history.append({"role":"assistant","content":reply})
        st.stop()

    # Inventory questions
    q = parse_query(txt)
    mk, yr = q.get("make"), q.get("year")
    if mk and yr:
        cars = fetch_inventory(mk, yr)
        if cars:
            bullets = [
                f"- {c['year']} {c['make']} {c['model']}, PKR {c.get('price',0):,}, loc: {c.get('location','N/A')}"
                for c in cars[:MAX_SUGGESTIONS]
            ]
            inv = "InventoryData:\n" + "\n".join(bullets)
        else:
            inv = "InventoryData: No listings found for that make/year."
        st.session_state.history.append({"role":"assistant","content":inv})
        st.stop()

    # Fallback to LLM
    ctx = st.session_state.history[-(MAX_HISTORY_TURNS*2):]
    msgs = [{"role":"system","content":(
        "You are Otoz.ai’s car-sales assistant. Use inventory data when possible; otherwise be helpful."
    )}]
    msgs.extend(ctx); msgs.append({"role":"user","content":txt})

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=msgs,
            temperature=0.7,
            max_tokens=400
        )
        bot = resp.choices[0].message.content.strip()
    except OpenAIError as e:
        st.error("AI service error.")
        st.write(f"{e}")
        bot = "Sorry, I'm having trouble."

    st.session_state.history.append({"role":"assistant","content":bot})
# ─────────────────────────────────────────────────────────────────────────────
# End of app.py
