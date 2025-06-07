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

# 2. Initialize history and pending context
if "history" not in st.session_state:
    st.session_state.history = []
if "pending_make" not in st.session_state:
    st.session_state.pending_make = None
if "pending_year" not in st.session_state:
    st.session_state.pending_year = None

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

# 4. Single-hit chat input
user_input = st.chat_input("Ask me about our cars…")
if user_input:
    text = user_input.strip()
    lc = text.lower()

    # 4.1 Input validation
    if len(text) < MIN_QUERY_LENGTH:
        st.warning(f"Please enter at least {MIN_QUERY_LENGTH} characters.")
    elif len(text) > MAX_QUERY_LENGTH:
        st.warning(f"Your query is too long—max {MAX_QUERY_LENGTH} characters.")
    else:
        st.session_state.history.append({"role": "user", "content": text})
        processed = False

        # 4A. If both pending_make and pending_year are set, finalize lookup now
        if st.session_state.pending_make and st.session_state.pending_year:
            make = st.session_state.pending_make
            year = st.session_state.pending_year
            cars = fetch_inventory(make, year)
            if cars:
                bullets = [
                    f"- {c['year']} {c['make']} {c['model']}, PKR {c['price']:,}, location: {c['location']}"
                    for c in cars[:MAX_SUGGESTIONS]
                ]
                reply = "Here are the matching cars:\n" + "\n".join(bullets)
            else:
                reply = (
                    "I’m sorry, we don’t have that exact model right now. "
                    "For assistance, please email us at inquiry@otoz.ai."
                )
            st.session_state.history.append({"role": "assistant", "content": reply})
            st.session_state.pending_make = None
            st.session_state.pending_year = None
            processed = True

        # 4B. If pending_make only and user gives year
        elif st.session_state.pending_make and re.fullmatch(r"(19|20)\d{2}", text):
            make = st.session_state.pending_make
            year = int(text)
            cars = fetch_inventory(make, year)
            if cars:
                bullets = [
                    f"- {c['year']} {c['make']} {c['model']}, PKR {c['price']:,}, location: {c['location']}"
                    for c in cars[:MAX_SUGGESTIONS]
                ]
                reply = "Here are the matching cars:\n" + "\n".join(bullets)
            else:
                reply = (
                    "I’m sorry, we don’t have that exact model right now. "
                    "For assistance, please email us at inquiry@otoz.ai."
                )
            st.session_state.history.append({"role": "assistant", "content": reply})
            st.session_state.pending_make = None
            processed = True

        # 4C. If pending_year only and user gives make
        elif st.session_state.pending_year and any(mk.lower() == lc for mk in ["honda","toyota","bmw","suzuki","nissan","mercedes"]):
            year = st.session_state.pending_year
            make = next(mk for mk in ["Honda","Toyota","BMW","Suzuki","Nissan","Mercedes"] if mk.lower() == lc)
            cars = fetch_inventory(make, year)
            if cars:
                bullets = [
                    f"- {c['year']} {c['make']} {c['model']}, PKR {c['price']:,}, location: {c['location']}"
                    for c in cars[:MAX_SUGGESTIONS]
                ]
                reply = "Here are the matching cars:\n" + "\n".join(bullets)
            else:
                reply = (
                    "I’m sorry, we don’t have that exact model right now. "
                    "For assistance, please email us at inquiry@otoz.ai."
                )
            st.session_state.history.append({"role": "assistant", "content": reply})
            st.session_state.pending_year = None
            processed = True

        # 4D. Count-style queries
        if not processed:
            m_count = re.match(r"how many cars of (\w+).*?(\d{4})", lc)
            if m_count:
                make = m_count.group(1).capitalize()
                year = int(m_count.group(2))
                cars = fetch_inventory(make, year)
                reply = f"We have {len(cars)} {make} cars from {year} in our inventory."
                st.session_state.history.append({"role": "assistant", "content": reply})
                processed = True

        # 4E. Max-suggestions queries
        if not processed and ("most number" in lc or "max suggestions" in lc):
            reply = f"I can suggest up to {MAX_SUGGESTIONS} cars at a time."
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True

        # 4F. Inventory queries: detect both make and year
        if not processed:
            year_match = re.search(r"\b(19|20)\d{2}\b", text)
            make_match = next((mk for mk in ["Honda","Toyota","BMW","Suzuki","Nissan","Mercedes"] if mk.lower() in lc), None)
            year = int(year_match.group()) if year_match else None
            make = make_match
            if make and year:
                cars = fetch_inventory(make, year)
                if cars:
                    bullets = [
                        f"- {c['year']} {c['make']} {c['model']}, PKR {c['price']:,}, location: {c['location']}"
                        for c in cars[:MAX_SUGGESTIONS]
                    ]
                    reply = "Here are the matching cars:\n" + "\n".join(bullets)
                else:
                    reply = (
                        "I’m sorry, we don’t have that exact model right now. "
                        "For assistance, please email us at inquiry@otoz.ai."
                    )
                st.session_state.history.append({"role": "assistant", "content": reply})
                processed = True
            # Only make but no year
            elif make and not year:
                st.session_state.history.append({"role": "assistant", "content": f"Which year of {make} are you interested in?"})
                st.session_state.pending_make = make
                processed = True
            # Only year but no make
            elif year and not make:
                st.session_state.history.append({"role": "assistant", "content": f"Which make are you looking for from {year}?"})
                st.session_state.pending_year = year
                processed = True

        # 4G. Graceful fallback
        if not processed:
            fallback = (
                "For questions beyond our inventory, please contact inquiry@otoz.ai or visit otoz.ai/help."
            )
            st.session_state.history.append({"role": "assistant", "content": fallback})

# 5. Render chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ─────────────────────────────────────────────────────────────────────────────
# End of script
