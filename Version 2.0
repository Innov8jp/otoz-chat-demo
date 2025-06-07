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
# Expected CSV columns—rename if your CSV uses different headers
CSV_COLUMNS = ["year", "make", "model", "price", "location"]

DEFAULT_MODEL     = "gpt-4o-mini"
MIN_QUERY_LENGTH  = 3
MAX_QUERY_LENGTH  = 200
MAX_HISTORY_TURNS = 10
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

# 5. Parse make/year from text
def parse_inventory_query(text: str) -> dict:
    info = {}
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m:
        info["year"] = int(m.group())
    # dynamic makes could be loaded here
    for make in ["Honda", "Toyota", "BMW", "Suzuki", "Nissan", "Mercedes"]:
        if make.lower() in text.lower():
            info["make"] = make
            break
    return info

# 6A. Fetch via Rails API
def fetch_inventory_from_api(make: str, year: int) -> list:
    try:
        resp = requests.get(INVENTORY_API_URL, params={"make":make,"year":year}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.write(f"Rails API error: {e}")
        return []

# 6B. Fetch and parse the CSV
def fetch_inventory_from_csv(url: str, make: str, year: int) -> list:
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        text = resp.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        results = []
        for row in reader:
            # Normalize keys and values
            row_year = int(row.get("year", 0))
            row_make = row.get("make", "").strip()
            if row_year == year and row_make.lower() == make.lower():
                # Map only expected columns
                item = {col: row.get(col, "").strip() for col in CSV_COLUMNS}
                # Convert price to int if possible
                try:
                    item["price"] = int(item["price"])
                except ValueError:
                    pass
                results.append(item)
        return results
    except Exception as e:
        st.error("⚠️ CSV lookup failed.")
        st.write(f"**Debug info:** {e}")
        return []

# 7. Display history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 8. Get user input
user_input = st.chat_input("Ask me about our cars …")
if user_input:
    # Validation
    if len(user_input.strip()) < MIN_QUERY_LENGTH:
        st.warning(f"Please enter at least {MIN_QUERY_LENGTH} characters.")
    elif len(user_input) > MAX_QUERY_LENGTH:
        st.warning(f"Your query is too long—max {MAX_QUERY_LENGTH} characters.")
    else:
        st.session_state.history.append({"role":"user","content":user_input})
        parsed = parse_inventory_query(user_input)
        make = parsed.get("make")
        year = parsed.get("year")

        cars = []
        if make and year:
            # First try Rails API
            cars = fetch_inventory_from_api(make, year)
            # Fallback to CSV if empty
            if not cars:
                cars = fetch_inventory_from_csv(DEALER_CSV_URL, make, year)

        if cars:
            bullets = [
                f"- {c['year']} {c['make']} {c['model']}, PKR {c.get('price',0):,}, location: {c.get('location','N/A')}"
                for c in cars[:5]
            ]
            reply = "InventoryData:\n" + "\n".join(bullets)
        else:
            reply = "InventoryData: No listings found for that make/year."

        # Build LLM messages
        history = st.session_state.history[-(MAX_HISTORY_TURNS*2):]
        messages = [{"role":"system","content":(
            "You are Otoz.ai’s official car-sales assistant. "
            "Use inventory data when available; otherwise, apologize."
        )}]
        messages.extend(history)
        messages.append({"role":"user","content":user_input})

        # Call OpenAI
        try:
            resp = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=400
            )
            bot_reply = resp.choices[0].message.content.strip()
        except OpenAIError as e:
            st.error("⚠️ AI service error.")
            st.write(f"Debug: {e}")
            bot_reply = "Sorry, I'm having trouble right now."

        # Append and display
        st.session_state.history.append({"role":"assistant","content": reply + "\n\n" + bot_reply})

# ─────────────────────────────────────────────────────────────────────────────
# End of app.py
