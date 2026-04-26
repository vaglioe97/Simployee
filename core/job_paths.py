JOB_PATHS = {
    "junior_data_analyst": {
        "id": "junior_data_analyst",
        "title": "Junior Data Analyst",
        "company": "NovaRetail Inc.",
        "industry": "Retail & E-commerce",
        "description": (
            "NovaRetail Inc. is a growing retail company with presence in 5 countries. "
            "The data team supports business decisions across sales, inventory, "
            "and customer behavior."
        ),
        "manager": "Sophie Chen",
        "manager_title": "Senior Data Analyst",
        "team": "Data & Analytics Team",
        "stack": ["SQL", "Python", "Excel", "Power BI"],
        "responsibilities": [
            "Clean and transform sales and inventory datasets",
            "Create weekly reports for the operations team",
            "Analyze customer behavior trends",
            "Maintain and update Power BI dashboards",
            "Handle ad-hoc data requests from the business team",
        ],
        "duration_weeks": 24,
        "level": "Entry Level / Junior",
        "schema": """
NovaRetail Inc. — Database Schema (use these exact table and column names in all SQL tasks):

Table: sales
  - order_id (INTEGER) — unique order identifier
  - product_name (TEXT) — name of the product sold
  - category (TEXT) — product category (e.g. Electronics, Apparel, Home, Food)
  - units_sold (INTEGER) — number of units in the order
  - unit_price (DECIMAL) — price per unit
  - total_revenue (DECIMAL) — units_sold * unit_price
  - sale_date (DATE) — date of the transaction (format: YYYY-MM-DD)
  - region (TEXT) — sales region (North, South, East, West, International)
  - store_id (INTEGER) — store where the sale occurred

Table: inventory
  - product_id (INTEGER) — unique product identifier
  - product_name (TEXT) — name of the product
  - category (TEXT) — product category
  - stock_level (INTEGER) — current units in stock
  - reorder_point (INTEGER) — minimum stock before reorder is triggered
  - last_restocked (DATE) — date of last restock

Table: customers
  - customer_id (INTEGER) — unique customer identifier
  - full_name (TEXT) — customer full name
  - email (TEXT) — customer email
  - region (TEXT) — customer region
  - signup_date (DATE) — date they joined NovaRetail
  - total_orders (INTEGER) — lifetime number of orders
  - total_spent (DECIMAL) — lifetime spend
"""
    }
}

def get_job_path(path_id):
    return JOB_PATHS.get(path_id)

def get_all_paths():
    return list(JOB_PATHS.values())