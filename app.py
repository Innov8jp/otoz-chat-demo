# ======================================================
# STAGE 3: DATA LOADING TEST
# ======================================================
import streamlit as st
import traceback
import pandas as pd
import random
from datetime import datetime
import os
import logging

st.set_page_config(page_title="App Test - Stage 3")
st.title("✅ Application Test - Stage 2 Passed")
st.write("---")
st.header("Running Stage 3: Testing Data Loading Logic...")

# This is the final and most complex test.
# We will define and run the load_inventory() function.
try:
    st.write("Defining constants needed for data loading...")
    # --- Define the necessary constants ---
    INVENTORY_FILE_PATH = 'Inventory Agasta.csv'
    MILEAGE_RANGE = (5_000, 150_000)
    CAR_MAKERS_AND_MODELS = {
        "Toyota": ["Aqua", "Vitz", "Corolla", "Prius"],
        "Honda": ["Fit", "Vezel", "CR-V"],
        "Mercedes-Benz": ["C-Class", "E-Class"],
        "BMW": ["3 Series", "5 Series"]
    }
    CAR_COLORS = ['White', 'Black', 'Silver', 'Gray', 'Blue', 'Red']
    PORTS_BY_COUNTRY = {"Kenya": ["Mombasa"], "Pakistan": ["Karachi"], "Tanzania": ["Dar es Salaam"]}
    st.write("Constants defined successfully.")

    st.write("Defining `load_inventory` function...")
    # --- This is the function we are testing ---
    def load_inventory():
        df = None
        if os.path.exists(INVENTORY_FILE_PATH):
            try:
                df_from_file = pd.read_csv(INVENTORY_FILE_PATH)
                if not df_from_file.empty:
                    df = df_from_file
                else:
                    logging.warning("Inventory CSV file is empty. Generating sample data.")
            except Exception as read_error:
                logging.error(f"Could not read CSV file: {read_error}. Generating sample data.")
        
        if df is None:
            car_data = []
            current_year = datetime.now().year
            for make, models in CAR_MAKERS_AND_MODELS.items():
                for model in models:
                    for _ in range(3):
                        year = random.randint(current_year - 8, current_year - 1)
                        price = int(2_000_000 * (0.85 ** (current_year - year)) * random.uniform(0.9, 1.1))
                        car_data.append({'make': make, 'model': model, 'year': year, 'price': max(300_000, price)})
            df = pd.DataFrame(car_data)
        
        defaults = {
            'mileage': lambda: random.randint(*MILEAGE_RANGE), 'location': lambda: random.choice(list(PORTS_BY_COUNTRY.keys())),
            'fuel': 'Gasoline', 'transmission': lambda: random.choice(["Automatic", "Manual"]),
            'color': lambda: random.choice(CAR_COLORS), 'grade': lambda: random.choice(["4.5", "4.0", "3.5", "R"])
        }
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = [default() if callable(default) else default for _ in range(len(df))]
        
        df.reset_index(drop=True, inplace=True)
        df['image_url'] = [f"https://placehold.co/600x400/grey/white?text={r.make}+{r.model}" for r in df.itertuples()]
        df['id'] = [f"VID{i:04d}" for i in df.index]
        return df
        
    st.write("`load_inventory` function defined successfully.")

    st.write("---")
    st.write("Attempting to execute `load_inventory()`...")
    # --- Now, we call the function ---
    inventory_df = load_inventory()

    st.success("`load_inventory()` executed successfully!")
    st.write("A sample inventory DataFrame was created with the following details:")
    st.write(f"- **Number of vehicles generated:** `{len(inventory_df)}`")
    st.write(f"- **Data columns:** `{list(inventory_df.columns)}`")
    st.dataframe(inventory_df.head())

    st.info("Please reply with the message 'Stage 3 works' if you see this.")

except Exception as e:
    st.error("A critical error occurred during Stage 3 (Data Loading).")
    st.error("This means the problem is inside the logic of the `load_inventory` function.")
    st.error(f"Error Type: {type(e).__name__}")
    st.error(f"Error Details: {e}")
    st.code(traceback.format_exc())

# We stop the script here on purpose.
st.stop()
