import os
import re
import streamlit as st
import openai
import requests

# 1. Load your OpenAI API key from an environment variable:
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Otoz.ai Chat Demo", layout="wide")
st.title("Otoz.ai Inventory-Aware Chatbot")

# 2. Keep all messages here (in Streamlit’s session state):
if "history" not in st.session_state:
    st.session_state.history = []

# 3. Helper: detect a simple “make + year” query
def parse_inventory_query(text):
    info = {}
    # Find a 4-digit year (1900–2099)
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        info["year"] = int(year_match.group())

    # Check for common car makes in the text
    for make in ["Honda", "Toyota", "BMW", "Suzuki", "Nissan", "Mercedes"]:
        if make.lower() in text.lower():
            info["make"] = make
            break

    return info

# 4. Helper: call your Rails inventory API
def fetch_inventory_from_api(make=None, year=None):
    if not (make and year):
        return []
    # Replace this URL with your real inventory endpoint:
    api_url = "https://api.otoz.ai/inventory"
    params = {"make": make, "year": year}
    try:
        resp = requests.get(api_url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error fetching inventory: {e}")
        return []

# 5. Show past chat messages
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Bot:** {msg['content']}")

# 6. Input box for the user
user_input = st.text_input("Ask me about our cars …", key="input")

if user_input:
    # 7. Add user’s message to history
    st.session_state.history.append({"role": "user", "content": user_input})

    # 8. Check if user is asking about “make + year”
    parsed = parse_inventory_query(user_input)
    inventory_snippet = None
    if parsed.get("make") and parsed.get("year"):
        cars = fetch_inventory_from_api(parsed["make"], parsed["year"])
        if cars:
            bullets = []
            for c in cars[:5]:
                price = "{:,}".format(c.get("price", 0))
                bullets.append(
                    f"- {c['year']} {c['make']} {c['model']}, PKR {price}, location: {c.get('location','N/A')}"
                )
            inventory_snippet = "InventoryData:\n" + "\n".join(bullets)
        else:
            inventory_snippet = (
                f"InventoryData: No {parsed['year']} {parsed['make']} listings right now."
            )

    # 9. Build messages for GPT
    messages = []
    system_prompt = (
        "You are Otoz.ai’s official car-sales assistant. "
        "Always answer using real inventory data if available. "
        "If you don’t know, say 'I’m sorry, I don’t have that information right now.'"
    )
    messages.append({"role": "system", "content": system_prompt})

    if inventory_snippet:
        messages.append({"role": "assistant", "content": inventory_snippet})

    # 10. Include the entire chat history so far
    messages.extend(st.session_state.history)

    # 11. Finally, add the new user message
    messages.append({"role": "user", "content": user_input})

    # 12. Call OpenAI’s ChatCompletion
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
        bot_reply = response.choices[0].message["content"].strip()
    except Exception as e:
        bot_reply = f"Error calling OpenAI: {e}"

    # 13. Add the bot’s reply to history
    st.session_state.history.append({"role": "assistant", "content": bot_reply})

    # 14. (Removed) Clear the input box
    # st.session_state.input = ""
