import csv
import random
from datetime import date, timedelta

random.seed(42)

PRODUCTS = [
    ("Wireless Headphones", "Electronics"),
    ("USB-C Hub", "Electronics"),
    ("Bluetooth Speaker", "Electronics"),
    ("Running Shoes", "Apparel"),
    ("Yoga Mat", "Sports"),
    ("Coffee Maker", "Home"),
    ("Desk Lamp", "Home"),
    ("Notebook Set", "Office"),
    ("Water Bottle", "Sports"),
    ("Backpack", "Apparel"),
    ("Sunglasses", "Apparel"),
    ("Protein Powder", "Food"),
    ("Green Tea Pack", "Food"),
    ("Monitor Stand", "Office"),
    ("Mechanical Keyboard", "Electronics"),
]

REGIONS = ["North", "South", "East", "West", "International"]
STORES = [101, 102, 103, 104, 105, 106, 107, 108]

PRICES = {
    "Wireless Headphones": 89.99,
    "USB-C Hub": 34.99,
    "Bluetooth Speaker": 59.99,
    "Running Shoes": 119.99,
    "Yoga Mat": 29.99,
    "Coffee Maker": 79.99,
    "Desk Lamp": 39.99,
    "Notebook Set": 14.99,
    "Water Bottle": 19.99,
    "Backpack": 54.99,
    "Sunglasses": 44.99,
    "Protein Powder": 49.99,
    "Green Tea Pack": 12.99,
    "Monitor Stand": 34.99,
    "Mechanical Keyboard": 129.99,
}

def generate_sales(filepath, num_rows=500):
    start_date = date(2024, 1, 1)
    end_date = date(2024, 3, 31)
    delta = (end_date - start_date).days

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "product_name", "category",
            "units_sold", "unit_price", "total_revenue",
            "sale_date", "region", "store_id"
        ])
        for i in range(1, num_rows + 1):
            product, category = random.choice(PRODUCTS)
            units = random.randint(1, 10)
            price = PRICES[product]
            revenue = round(units * price, 2)
            sale_date = start_date + timedelta(days=random.randint(0, delta))
            region = random.choice(REGIONS)
            store = random.choice(STORES)

            # Introduce some dirt for realism
            if random.random() < 0.03:
                product = ""          # missing product name
            if random.random() < 0.02:
                sale_date = "03/15/2024"  # wrong date format

            writer.writerow([
                i, product, category,
                units, price, revenue,
                sale_date, region, store
            ])

    print(f"Generated {num_rows} rows -> {filepath}")

def generate_categories(filepath):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "categories_raw"

    ws.append(["category_id", "category_name", "department"])

    raw_categories = [
        (1,  "Electronics",   "Tech"),
        (2,  "electronics",   "Tech"),
        (3,  "ELECTRONICS",   "Tech"),
        (4,  "Apparel",       "Fashion"),
        (5,  "apparel",       "Fashion"),
        (6,  "Apparel ",      "Fashion"),   # trailing space
        (7,  "Home",          "Living"),
        (8,  "HOME",          "Living"),
        (9,  "home goods",    "Living"),
        (10, "Food",          "Grocery"),
        (11, "food",          "Grocery"),
        (12, "FOOD & BEV",    "Grocery"),
        (13, "Sports",        "Active"),
        (14, "sports",        "Active"),
        (15, "Sport",         "Active"),    # typo
        (16, "Office",        "Work"),
        (17, "office",        "Work"),
        (18, "Office Supplies","Work"),
        (19, "",              "Unknown"),   # blank
        (20, "N/A",           "Unknown"),  # invalid
        (21, "TBD",           "Unknown"),  # invalid
    ]

    for row in raw_categories:
        ws.append(row)

    wb.save(filepath)
    print(f"Generated categories -> {filepath}")

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    generate_sales("data/novaretail_sales_q1_2024.csv")
    generate_categories("data/novaretail_categories_raw.xlsx")