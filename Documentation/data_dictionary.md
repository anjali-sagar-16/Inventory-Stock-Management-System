# Data dictionary
| Table | Column | Type | Constraints / notes |
|---|---|---|---|
| users | user_id | INTEGER | PK |
| | username | TEXT | NOT NULL UNIQUE |
| | password_hash | TEXT | NOT NULL (Werkzeug hash) |
| | full_name | TEXT | optional |
| | role | TEXT | CHECK admin/staff, default staff |
| | is_active | INTEGER | 0/1, default 1 |
| | created_at | TEXT | default CURRENT_TIMESTAMP |
| suppliers | supplier_id | INTEGER | PK |
| | supplier_name | TEXT | NOT NULL |
| | phone, email, address | TEXT | optional |
| | created_at | TEXT | default now |
| products | product_id | INTEGER | PK |
| | product_code | TEXT | UNIQUE, optional |
| | product_name | TEXT | NOT NULL |
| | description | TEXT | optional |
| | unit_price | REAL | NULL or >= 0 |
| | quantity | INTEGER | NOT NULL default 0, CHECK >= 0 |
| | reorder_level | INTEGER | NOT NULL default 0, CHECK >= 0 |
| | supplier_id | INTEGER | nullable FK -> suppliers |
| stock_movements | movement_id | INTEGER | PK |
| | product_id | INTEGER | FK -> products, NOT NULL |
| | user_id | INTEGER | FK -> users, NOT NULL |
| | movement_type | TEXT | CHECK IN/OUT |
| | quantity | INTEGER | CHECK > 0 |
| | notes | TEXT | optional |
| | movement_date | TEXT | default now |
| sales | sale_id | INTEGER | PK |
| | user_id | INTEGER | FK -> users |
| | sale_date | TEXT | default now |
| | total_amount | REAL | CHECK >= 0, computed server-side |
| sale_items | sale_item_id | INTEGER | PK |
| | sale_id | INTEGER | FK -> sales |
| | product_id | INTEGER | FK -> products |
| | quantity | INTEGER | CHECK > 0 |
| | unit_price | REAL | price at time of sale |
| | line_total | REAL | quantity x unit_price |
