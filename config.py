# config.py

# --- Application & Seller Info ---
BOT_NAME = "Sparky"
PAGE_TITLE = f"{BOT_NAME} - AI Sales Assistant"
PAGE_ICON = "🚗"
SELLER_INFO = {
    "name": "Otoz.ai", "address": "1-chōme-9-1 Akasaka, Minato City, Tōkyō-to 107-0052, Japan",
    "phone": "+81-3-1234-5678", "email": "sales@otoz.ai"
}
LOGO_PATH = "otoz_logo.png"

# --- Data & File Paths ---
INVENTORY_FILE_PATH = 'Inventory Agasta.csv'
MILEAGE_RANGE = (5_000, 150_000)

# --- Shipping Cost Parameters (in JPY) ---
DOMESTIC_TRANSPORT = 50_000
FREIGHT_COST = 150_000
INSURANCE_RATE = 0.025

# --- Vehicle & Destination Data ---
CAR_MAKERS_AND_MODELS = {
    "Toyota": ["Aqua", "Vitz", "Passo", "Corolla", "Prius", "Harrier", "RAV4", "Land Cruiser", "HiAce"],
    "Honda": ["Fit", "Vezel", "CR-V", "Civic", "Accord", "N-BOX", "Freed"],
    "Nissan": ["Note", "Serena", "X-Trail", "Leaf", "Skyline", "March", "Juke"],
    "Mazda": ["Demio", "CX-5", "CX-8", "Mazda3", "Mazda6", "Roadster"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "GLC", "A-Class"],
    "BMW": ["3 Series", "5 Series", "X1", "X3", "X5", "1 Series"]
}
CAR_COLORS = ['White', 'Black', 'Silver', 'Gray', 'Blue', 'Red', 'Beige', 'Brown', 'Green', 'Pearl White', 'Dark Blue', 'Maroon']
PORTS_BY_COUNTRY = {
    "Australia": ["Adelaide", "Brisbane", "Fremantle", "Melbourne", "Sydney"], "Canada": ["Halifax", "Vancouver"],
    "Chile": ["Iquique", "Valparaíso"], "Germany": ["Bremerhaven", "Hamburg"], "Ireland": ["Cork", "Dublin"],
    "Kenya": ["Mombasa"], "Malaysia": ["Port Klang"], "New Zealand": ["Auckland", "Lyttelton", "Napier", "Wellington"],
    "Pakistan": ["Karachi", "Port Qasim"], "Tanzania": ["Dar es Salaam"], "Thailand": ["Laem Chabang"],
    "United Arab Emirates": ["Jebel Ali (Dubai)"], "United Kingdom": ["Bristol", "Liverpool", "Southampton", "Tilbury"],
    "United States": ["Baltimore", "Jacksonville", "Long Beach", "Newark", "Tacoma"], "Zambia": ["(Via Dar es Salaam, Tanzania)"]
}
