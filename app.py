# Updated shipping cost parameters (in JPY)
DOMESTIC_TRANSPORT = 50000  # 50,000 JPY
FREIGHT_COST = 150000  # 150,000 JPY
INSURANCE_RATE = 0.02  # 2% of base price

def calculate_total_price(base_price: float, option: str) -> Dict[str, float]:
    """Calculate total price with breakdown of components"""
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0:
            raise ValueError("Invalid base price")
        
        breakdown = {
            'base_price': base_price,
            'domestic_transport': 0,
            'freight_cost': 0,
            'insurance': 0,
            'total_price': base_price
        }
        
        if option == "FOB":
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
            breakdown['total_price'] += DOMESTIC_TRANSPORT
        elif option == "C&F":
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
            breakdown['freight_cost'] = FREIGHT_COST
            breakdown['total_price'] += DOMESTIC_TRANSPORT + FREIGHT_COST
        elif option == "CIF":
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
            breakdown['freight_cost'] = FREIGHT_COST
            breakdown['insurance'] = INSURANCE_RATE * base_price
            breakdown['total_price'] += DOMESTIC_TRANSPORT + FREIGHT_COST + breakdown['insurance']
            
        return breakdown
    except Exception as e:
        logging.error(f"Error calculating total price: {str(e)}")
        return {
            'base_price': base_price,
            'domestic_transport': 0,
            'freight_cost': 0,
            'insurance': 0,
            'total_price': base_price
        }

def display_car_card(car: Dict[str, Any], shipping_option: str):
    try:
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(car['image_url'], use_column_width=True)
            with col2:
                st.subheader(f"{car.get('year', 'Unknown')} {car.get('make', 'Unknown')} {car.get('model', '')}")
                
                st.write(f"**ID:** {car.get('id', 'N/A')}")
                st.write(f"**Location:** {car.get('location', 'N/A')}")
                
                mileage = car.get('mileage', None)
                st.write(f"**Mileage:** {int(mileage):,} km" if pd.notnull(mileage) else "**Mileage:** N/A")
                
                st.write(f"**Color:** {car.get('color', 'N/A')}  |  **Transmission:** {car.get('transmission', 'N/A')}")
                st.write(f"**Fuel:** {car.get('fuel', 'N/A')}  |  **Grade:** {car.get('grade', 'N/A')}")
                st.write(f"**Base Price:** ¥{car.get('price', 0):,}")
                
                price_breakdown = calculate_total_price(car['price'], shipping_option)
                st.success(f"**Total Price ({shipping_option}): ¥{int(price_breakdown['total_price']):,}**")
                
                # Display price breakdown on expander
                with st.expander("Price Breakdown"):
                    st.write(f"- Base Price: ¥{price_breakdown['base_price']:,}")
                    if shipping_option != "Ex-Works":
                        st.write(f"- Domestic Transport: ¥{price_breakdown['domestic_transport']:,}")
                        if shipping_option in ["C&F", "CIF"]:
                            st.write(f"- Freight Cost: ¥{price_breakdown['freight_cost']:,}")
                        if shipping_option == "CIF":
                            st.write(f"- Insurance ({INSURANCE_RATE*100}%): ¥{price_breakdown['insurance']:,.0f}")
                    st.write(f"**Total: ¥{price_breakdown['total_price']:,.0f}**")
    except Exception as e:
        st.error(f"Error displaying car card: {str(e)}")
