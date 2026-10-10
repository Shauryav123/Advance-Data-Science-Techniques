"""
Generate Canonical Indian Dish and Restaurant Name Maps
Maps synthetic numbers to authentic, realistic culinary entities
"""

# 50 Main Courses
MAIN_COURSES = [
    "Butter Chicken", "Paneer Butter Masala", "Hyderabadi Chicken Biryani", "Mutton Rogan Josh",
    "Dal Makhani", "Chole Bhature", "Palak Paneer", "Kadai Paneer", "Chicken Tikka Masala",
    "Dum Aloo Kashmiri", "Kadhai Chicken", "Dal Tadka", "Fish Curry Malabar", "Prawn Masala",
    "Chettinad Chicken", "Paneer Lababdar", "Bhindi Masala", "Chicken Korma", "Mutton Korma",
    "Vegetable Biryani", "Egg Curry", "Mushroom Masala", "Rajma Chawal", "Paneer Do Pyaza",
    "Chicken Chettinad", "Malai Kofta", "Methi Malai Matar", "Baingan Bharta", "Jeera Rice",
    "Chicken Sukka", "Aloo Gobi Adraki", "Shahi Paneer", "Chicken Do Pyaza", "Prawn Pepper Fry",
    "Kashmiri Pulao", "Veg Jalfrezi", "Keema Matar", "Sambar Rice", "Curd Rice",
    "Bisi Bele Bath", "Chicken Fried Rice", "Veg Hakka Noodles", "Schezwan Chicken",
    "Gobi Manchurian Gravy", "Chilli Chicken Gravy", "Paneer Manchurian", "Chicken Shawarma Plate",
    "Hyderabadi Mutton Biryani", "Lucknowi Veg Biryani", "Amritsari Kulcha Platter"
]

# 20 Appetizers
APPETIZERS = [
    "Paneer Tikka", "Chicken Tikka", "Tandoori Chicken", "Hara Bhara Kabab", "Chicken Seekh Kabab",
    "Fish Amritsari", "Dahi Ke Kebab", "Mutton Galouti Kabab", "Crispy Corn Chilli Pepper",
    "Chicken Malai Tikka", "Tandoori Soya Chaap", "Paneer Malai Tikka", "Chilli Paneer Dry",
    "Chicken 65", "Gobi 65", "Dragon Chicken", "Mushroom Kurkure", "Fish Tikka",
    "Tandoori Prawns", "Veg Spring Rolls"
]

# 15 Snacks
SNACKS = [
    "Masala Dosa", "Pav Bhaji", "Samosa Chaat", "Pani Puri Platter", "Vada Pav",
    "Aloo Tikki Chaat", "Dahi Puri", "Kathi Roll Chicken", "Paneer Kathi Roll",
    "Bhel Puri", "Idli Vada Combo", "Cheese Garlic Bread", "Mirchi Bajji",
    "Chicken Momos Steamed", "Veg Momos Steamed"
]

# 20 Desserts
DESSERTS = [
    "Gulab Jamun", "Rasgulla", "Rasmalai", "Gajar Ka Halwa", "Kaju Katli",
    "Kulfi Falooda", "Shahi Tukda", "Moong Dal Halwa", "Chocolate Brownie",
    "Pista Kulfi", "Matka Phirni", "Jalebi with Rabri", "Mishti Doi",
    "Gulab Jamun with Ice Cream", "Mango Kulfi", "Carrot Cake",
    "Basundi", "Payasam", "Mysore Pak", "Cheesecake Slice"
]

# 20 Beverages
BEVERAGES = [
    "Masala Chai", "Filter Coffee", "Mango Lassi", "Sweet Lassi", "Salted Mint Chaas",
    "Fresh Lime Soda", "Cold Coffee", "Badam Milk", "Nimbu Pani", "Watermelon Juice",
    "Virgin Mojito", "Blue Lagoon Cooler", "Iced Lemon Tea", "Rose Milk",
    "Tender Coconut Water", "Masala Buttermilk", "Thandai", "Oreo Milkshake",
    "Green Tea", "Cold Brew Coffee"
]

# Generate exact mappings for "Category N" -> Canonical Name
DISH_MAP = {}
for i, name in enumerate(MAIN_COURSES, 1):
    DISH_MAP[f"Main Dish {i}"] = name
for i, name in enumerate(APPETIZERS, 1):
    DISH_MAP[f"Appetizer {i}"] = name
for i, name in enumerate(SNACKS, 1):
    DISH_MAP[f"Snack {i}"] = name
for i, name in enumerate(DESSERTS, 1):
    DISH_MAP[f"Dessert {i}"] = name
for i, name in enumerate(BEVERAGES, 1):
    DISH_MAP[f"Beverage {i}"] = name

# Realistic brand names for Cloud Kitchens and Restaurants
BRAND_PREFIXES = [
    "Spice Garden", "Royal Biryani Darbar", "Urban Bowl Co.", "The Punjabi Rasoi",
    "Dosa Factory", "Tandoori Nights", "Rolls & Bowls Express", "Bawarchi Khana",
    "Chai & Samosa Hub", "Flavors of Malabar", "The Daily Thali", "Curry Leaf Kitchen",
    "Kebab Boulevard", "Chilli & Pepper Wok", "Mithai & Dessert Box", "Biryani Central",
    "Udupi Sagar Express", "The Great Indian Feast", "Kolkata Roll Corner", "Copper Chimney Kitchen"
]

RESTAURANT_MAP = {}
for i in range(1, 201):
    prefix = BRAND_PREFIXES[(i - 1) % len(BRAND_PREFIXES)]
    branch_num = ((i - 1) // len(BRAND_PREFIXES)) + 1
    RESTAURANT_MAP[f"Restaurant {i}"] = f"{prefix} #{branch_num}" if branch_num > 1 else prefix

if __name__ == "__main__":
    print(f"Mapped {len(DISH_MAP)} dishes and {len(RESTAURANT_MAP)} restaurants.")
