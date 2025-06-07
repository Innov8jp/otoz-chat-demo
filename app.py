import os
import re
import csv
import io
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Constants
CSV_URL           = (
    "https://s3.ap-northeast-1.amazonaws.com/"
    "otoz.ai/agasta/1821a7c5-c689-4ec2-bad0-25464a659173_agasta_stock.csv"
)
CSV_COLUMNS       = ["year", "make", "model", "price", "location"]
MIN_QUERY_LENGTH  = 3
MAX_QUERY_LENGTH  = 200
MAX_SUGGESTIONS   = 5
# ─────────────────────────────────────────────────────────────────────────────

# 1. Page setup
st.set_page_config(page_title="Otoz.ai Inventory-Aware Chatbot", layout="wide")
st.title("Otoz.ai Inventory-Aware Chatbot")

# 2. Initialize session state for history and user info
if "history" not in st.session_state:
    st.session_state.history = []
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_country" not in st.session_state:
    st.session_state.user_country = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "pending_info" not in st.session_state:
    st.session_state.pending_info = None  # tracks asking name, country, email

# 3. Helper: fetch and filter inventory from CSV
def fetch_inventory(make: str, year: int) -> list[dict]:
    try:
        resp = requests.get(CSV_URL, timeout=5)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        results = []
        for row in reader:
            try:
                row_year = int(row.get("year", 0))
            except ValueError:
                continue
            if row_year == year and row.get("make", "").strip().lower() == make.lower():
                item = {col: row.get(col, "").strip() for col in CSV_COLUMNS}
                try:
                    item["price"] = int(item.get("price", 0))
                except (ValueError, TypeError):
                    item["price"] = None
                results.append(item)
        return results
    except requests.RequestException:
        return []

# 4. Initial greeting
if not st.session_state.history:
    greeting = (
        "Hi, thank you for contacting Otoz.ai! I'm here to help you find the perfect car."
        " To get started, may I have your name?"
    )
    st.session_state.history.append({"role": "assistant", "content": greeting})
    st.session_state.pending_info = "name"

# 5. Single-hit chat input
user_input = st.chat_input("Type your message…")
if user_input:
    text = user_input.strip()
    st.session_state.history.append({"role": "user", "content": text})
    processed = False

    # 5A. Collect user info sequence
    if st.session_state.pending_info:
        info = st.session_state.pending_info
        if info == "name":
            st.session_state.user_name = text
            reply = f"Nice to meet you, {text}! Which country are you contacting us from?"
            st.session_state.pending_info = "country"
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True
        elif info == "country":
            st.session_state.user_country = text
            reply = f"Thanks! Finally, could you please share your email address so we can follow up?"
            st.session_state.pending_info = "email"
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True
        elif info == "email":
            st.session_state.user_email = text
            reply = (
                f"Great, thank you {st.session_state.user_name}. "
                "I'll now work on your inquiry. What car make and year are you interested in?"
            )
            st.session_state.pending_info = None
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True

    # 5B. After info collected, handle inventory and other queries
    if not processed:
        lc = text.lower()
        # Validate length
        if len(text) < MIN_QUERY_LENGTH:
            st.session_state.history.append({"role": "assistant", "content": f"Please enter at least {MIN_QUERY_LENGTH} characters."})
            processed = True
        elif len(text) > MAX_QUERY_LENGTH:
            st.session_state.history.append({"role": "assistant", "content": f"Your message is too long; max {MAX_QUERY_LENGTH} characters."})
            processed = True

        # Inventory request: detect make and year
        if not processed:
            year_match = re.search(r"\b(19|20)\d{2}\b", text)
            make_match = next((mk for mk in ["Honda","Toyota","BMW","Suzuki","Nissan","Mercedes"] if mk.lower() in lc), None)
            if make_match and year_match:
                make = make_match
                year = int(year_match.group())
                # Acknowledge
                ack = f"Sure {st.session_state.user_name}, let me check our inventory for {make} {year}."
                st.session_state.history.append({"role": "assistant", "content": ack})
                cars = fetch_inventory(make, year)
                if cars:
                    bullets = [f"- {c['year']} {c['make']} {c['model']}, PKR {c['price']:,}, location: {c['location']}" for c in cars[:MAX_SUGGESTIONS]]
                    inv_reply = "Here are the matching cars:\n" + "\n".join(bullets)
                else:
                    inv_reply = (
                        "I’m sorry, we don’t have that exact model right now. "
                        "For assistance, please email us at inquiry@otoz.ai."
                    )
                st.session_state.history.append({"role": "assistant", "content": inv_reply})
                processed = True

        # 5C. Fallback for unsupported queries
        if not processed:
            fallback = (
                "For any further questions or assistance, please email us at inquiry@otoz.ai or visit otoz.ai/help."
            )
            st.session_state.history.append({"role": "assistant", "content": fallback})

# 6. Render chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# End of script
