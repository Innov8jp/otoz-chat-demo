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

# 1. Validate API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or not api_key.strip():
    st.error("Error: OPENAI_API_KEY not set.")
    st.stop()

# 2. Initialize OpenAI client
try:
    client = OpenAI(api_key=api_key)
except OpenAIError as e:
    st.error(f"OpenAI initialization error: {e}")
    st.stop()

# 3. Page setup
st.set_page_config(page_title="Otoz.ai Chat", layout="wide")

# 4. Single-hit chat input at top
user_input = st.chat_input("Ask me about our cars…")

# 5. Initialize history
if "history" not in st.session_state:
    st.session_state.history = []

# 6. Process new input
if user_input:
    text = user_input.strip()
    # 6.1 Validate length
    if len(text) < MIN_QUERY_LENGTH:
        st.warning(f"Please enter at least {MIN_QUERY_LENGTH} characters.")
    elif len(text) > MAX_QUERY_LENGTH:
        st.warning(f"Your query is too long—max {MAX_QUERY_LENGTH} characters.")
    else:
        st.session_state.history.append({"role": "user", "content": text})
        lc = text.lower()
        processed = False

        # 6A. Count-style questions
        m_count = re.match(r"how many cars of (\w+).*?(\d{4})", lc)
        if m_count:
            mk = m_count.group(1).capitalize()
            yr = int(m_count.group(2))
            cars = []
            try:
                resp = requests.get(CSV_URL, timeout=5)
                resp.raise_for_status()
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    if int(row.get("year", 0)) == yr and row.get("make", "").lower() == mk.lower():
                        cars.append(row)
            except Exception:
                pass
            reply = f"We have {len(cars)} {mk} cars from {yr} in our inventory."
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True

        # 6B. Max-suggestion questions
        elif "most number" in lc or "max suggestions" in lc:
            reply = f"I can suggest up to {MAX_SUGGESTIONS} cars at a time."
            st.session_state.history.append({"role": "assistant", "content": reply})
            processed = True

        # 6C. Inventory queries (make + year)
        else:
            year_match = re.search(r"\b(19|20)\d{2}\b", text)
            yr = int(year_match.group()) if year_match else None
            mk = None
            for candidate in ["Honda","Toyota","BMW","Suzuki","Nissan","Mercedes"]:
                if candidate.lower() in lc:
                    mk = candidate
                    break
            if mk and yr:
                cars = []
                try:
                    resp = requests.get(CSV_URL, timeout=5)
                    resp.raise_for_status()
                    reader = csv.DictReader(io.StringIO(resp.text))
                    for row in reader:
                        if int(row.get("year", 0)) == yr and row.get("make", "").lower() == mk.lower():
                            cars.append(row)
                except Exception:
                    pass
                if cars:
                    bullets = [
                        f"- {c['year']} {c['make']} {c['model']}, PKR {int(c.get('price',0)):,}, location: {c.get('location','N/A')}"
                        for c in cars[:MAX_SUGGESTIONS]
                    ]
                    inv_text = "InventoryData:\n" + "\n".join(bullets)
                else:
                    inv_text = "InventoryData: No listings found for that make/year."
                st.session_state.history.append({"role": "assistant", "content": inv_text})
                processed = True

        # 6D. Fallback to LLM
        if not processed:
            context = st.session_state.history[-(MAX_HISTORY_TURNS*2):]
            messages = [
                {"role": "system", "content": (
                    "You are Otoz.ai’s official car-sales assistant. "
                    "Use inventory data when relevant; otherwise be a helpful assistant."
                )}
            ] + context
            messages.append({"role": "user", "content": text})
            try:
                resp = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=400
                )
                bot_reply = resp.choices[0].message.content.strip()
            except OpenAIError:
                bot_reply = "Sorry, I'm having trouble right now."
            st.session_state.history.append({"role": "assistant", "content": bot_reply})

# 7. Display chat history below input
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ─────────────────────────────────────────────────────────────────────────────
# End of script
