import os
import re
import streamlit as st
from openai import OpenAI
import requests

# 1. Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Otoz.ai Chat Demo", layout="wide")
st.title("Otoz.ai Inventory-Aware Chatbot")

# 2. Initialize conversation history
if "history" not in st.session_state:
    st.session_state.history = []

# 3. Parse simple "make + year" queries
def parse_inventory_query(text: str) -> dict:
    info = {}
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        info["year"] = int(year_match.group())
    for make in ["Honda", "Toyota", "BMW", "Suzuki", "Nissan", "Mercedes"]:
        if make.lower() in text.lower():
            info["make"] = make
            break
    return info

# 4. Fetch inventory from Rails API
def fetch_inventory_from_api(make: str = None, year: int = None) -> list:
    if not (make and year):
        return []
    api_url = "https://api.otoz.ai/inventory"
    params = {"make": make, "year": year}
    try:
        resp = requests.get(api_url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Error fetching inventory: {e}")
        return []

# 5. Display chat history
for msg in st.session_state.history:
    prefix = "**You:**" if msg["role"] == "user" else "**Bot:**"
    st.markdown(f"{prefix} {msg['content']}")

# 6. User input field
user_input = st.text_input("Ask me about our cars …", key="input")
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    # 7. Handle inventory lookup
    parsed = parse_inventory_query(user_input)
    if parsed.get("make") and parsed.get("year"):
        cars = fetch_inventory_from_api(parsed["make"], parsed["year"])
        if cars:
            bullets = [f"- {c['year']} {c['make']} {c['model']}, PKR {c.get('price',0):,}, location: {c.get('location','N/A')}" for c in cars[:5]]
            st.session_state.history.append({"role": "assistant", "content": "InventoryData:\n" + "\n".join(bullets)})
        else:
            st.session_state.history.append({"role": "assistant", "content": f"InventoryData: No {parsed['year']} {parsed['make']} listings right now."})

    # 8. Build messages for LLM
    messages = [
        {"role": "system", "content": (
            "You are Otoz.ai’s official car-sales assistant. "
            "Use real inventory data when available. Otherwise, apologize for lack of info."
        )}
    ]
    messages.extend(st.session_state.history)

    # 9. Call the OpenAI Chat API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=400
        )
        bot_reply = response.choices[0].message.content.strip()
    except Exception as e:
        bot_reply = f"Error calling OpenAI: {e}"

    # 10. Record and display the assistant's reply
    st.session_state.history.append({"role": "assistant", "content": bot_reply})
