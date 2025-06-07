import os
import re
import csv
import io
import requests
import streamlit as st
from openai import OpenAI, OpenAIError

# ─────────────────────────────────────────────────────────────────────────────
# Constants & CSV API URL
INVENTORY_API_URL = "https://api.otoz.ai/inventory"
DEALER_CSV_URL    = (
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

# 1. Load and validate your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or not api_key.strip():
    st.error("Error: OPENAI_API_KEY environment variable not set.")
    st.stop()

# 2. Initialize the OpenAI client
try:
    client = OpenAI(api_key=api_key)
except OpenAIError as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

# 3. Page setup
st.set_page_config(page_title="Otoz.ai Chat Demo", layout="wide")
st.title("Otoz.ai Inventory-Aware Chatbot")

# 4. Initialize history
if "history" not in st.session_state:
    st.session_state.history = []

# 5. Helper: parse year/make
def parse_inventory_query(text: str) -> dict:
    info = {}
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m:
        info["year"] = int(m.group())
    for make in ["Honda", "Toyota", "BMW", "Suzuki", "Nissan", "Mercedes"]:
        if make.lower() in text.lower():
            info["make"] = make
            break
    return info

# 6A. Rails API fetch
def fetch_inventory_from_api(make: str, year: int) -> list:
    try:
        resp = requests.get(INVENTORY_API_URL, params={"make": make, "year": year}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []

# 6B. CSV fetch
def fetch_inventory_from_csv(url: str, make: str, year: int) -> list:
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        text = resp.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        results = []
        for row in reader:
            try:
                row_year = int(row.get("year", 0))
            except ValueError:
                continue
            if row_year == year and row.get("make","").strip().lower() == make.lower():
                item = {col: row.get(col,"").strip() for col in CSV_COLUMNS}
                try:
                    item["price"] = int(item["price"])
                except (ValueError, TypeError):
                    pass
                results.append(item)
        return results
    except Exception:
        return []

# 7. Display chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ─────────────────────────────────────────────────────────────────────────────
# 8. Chat form: single submission, auto-clear
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Ask me about our cars …")
    submit = st.form_submit_button("Send")

if submit and user_input:
    text = user_input.strip()

    # 8.1 Validate length
    if len(text) < MIN_QUERY_LENGTH:
        st.warning(f"Please enter at least {MIN_QUERY_LENGTH} characters.")
    elif len(text) > MAX_QUERY_LENGTH:
        st.warning(f"Your query is too long—max {MAX_QUERY_LENGTH} characters.")
    else:
        # Record user message
        st.session_state.history.append({"role": "user", "content": text})

        lc = text.lower()
        # 9A. Count queries
        m_count = re.match(r"how many cars of (\w+).*?(\d{4})", lc)
        if m_count:
            make = m_count.group(1).capitalize()
            year = int(m_count.group(2))
            cars = fetch_inventory_from_api(make, year) or fetch_inventory_from_csv(DEALER_CSV_URL, make, year)
            reply = f"We have {len(cars)} {make} cars from {year} in our inventory."
            st.session_state.history.append({"role": "assistant", "content": reply})
        # 9B. Max-suggestions queries
        elif "most number" in lc or "max suggestions" in lc:
            reply = f"I can suggest up to {MAX_SUGGESTIONS} cars at a time."
            st.session_state.history.append({"role": "assistant", "content": reply})
        else:
            # 10. Inventory lookup
            parsed = parse_inventory_query(text)
            make = parsed.get("make")
            year = parsed.get("year")
            cars = []
            if make and year:
                cars = fetch_inventory_from_api(make, year)
                if not cars:
                    cars = fetch_inventory_from_csv(DEALER_CSV_URL, make, year)

            # 11. Inventory reply
            if cars:
                bullets = [
                    f"- {c['year']} {c['make']} {c['model']}, PKR {c.get('price',0):,}, location: {c.get('location','N/A')}"
                    for c in cars[:MAX_SUGGESTIONS]
                ]
                inventory_text = "InventoryData:\n" + "\n".join(bullets)
            else:
                inventory_text = "InventoryData: No listings found for that make/year."

            # Append inventory only
            st.session_state.history.append({"role":"assistant","content": inventory_text})

            # Do not call LLM if it's purely inventory; skip to next
            st.experimental_rerun()

# ─────────────────────────────────────────────────────────────────────────────
# End of app.py
