### RECOMMENDED - Corrected Price Calculation Logic ###

# Import this at the top of your script to use type hints like 'Dict'
from typing import Dict, Any

# Define these constants at the top of your script
DOMESTIC_TRANSPORT = 50000  # 50,000 JPY
FREIGHT_COST = 150000  # 150,000 JPY
INSURANCE_RATE = 0.02   # 2%

def calculate_total_price(base_price: float, option: str) -> Dict[str, float]:
    """Calculate total price with a full breakdown of components."""
    try:
        if not isinstance(base_price, (int, float)) or base_price <= 0:
            raise ValueError("Invalid base price")
            
        breakdown = {
            'base_price': base_price,
            'domestic_transport': 0,
            'freight_cost': 0,
            'insurance': 0,
        }
        
        # FOB (Free On Board) includes domestic transport
        if option in ["FOB", "C&F", "CIF"]:
            breakdown['domestic_transport'] = DOMESTIC_TRANSPORT
            
        # C&F (Cost & Freight) includes ocean freight
        if option in ["C&F", "CIF"]:
            breakdown['freight_cost'] = FREIGHT_COST
            
        # CIF (Cost, Insurance & Freight) includes insurance
        if option == "CIF":
            # --- THIS IS THE CORRECTION ---
            # Insurance should be calculated on the C&F value (Base Price + Freight)
            cost_and_freight_value = base_price + breakdown['freight_cost']
            breakdown['insurance'] = cost_and_freight_value * INSURANCE_RATE
            # --- END OF CORRECTION ---
            
        # The total price is the sum of all components
        breakdown['total_price'] = sum(breakdown.values())
        return breakdown

    except Exception as e:
        # It's good practice to log errors
        print(f"Error calculating total price: {e}") 
        # Return a default breakdown on error
        return { 'base_price': base_price, 'domestic_transport': 0, 'freight_cost': 0, 'insurance': 0, 'total_price': base_price }
