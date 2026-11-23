# Implementation report

## 1. Repository inspection / gap analysis
No existing repository was supplied, so this is a greenfield build from the specification. Nothing was overwritten.
Not delivered (need the team): ER diagram, DFDs, architecture diagram, UML sequence diagram, screenshots,
WBS/Gantt/risk register, Jira and GitHub activity. No external action was performed.

## 2. FR mapping
| FR | Implemented in |
|----|----------------|
| FR-01 | `routes/auth.py` (Werkzeug hashes, session, inactive rejected, `login_required` on every business route) |
| FR-02 | `routes/catalog.py` products; quantity forced to 0 on create and not editable in the form |
| FR-03 | `routes/catalog.py` suppliers; delete unassigns linked products (supplier_id NULL) in one transaction |
| FR-04/05 | `services.record_movement`, `routes/inventory.py` |
| FR-06/07/08 | `services.create_sale` (aggregates duplicates, server-side totals, one `BEGIN IMMEDIATE` transaction, OUT movements) |
| FR-09/10 | `routes/main.py`, `dashboard.html`, Low badge on product pages |

## 3. Schema
Exactly the agreed baseline (`database/schema.sql`) plus indexes and `CHECK (is_active IN (0,1))`, `sales.total_amount >= 0`.
`init-db` uses `CREATE TABLE IF NOT EXISTS`, so it never drops data. No migration tool.

## 4. Assumptions / open decisions (need team confirmation)
- Roles: admin and staff have identical permissions (matrix not approved).
- Supplier delete: linked products are unassigned, not blocked.
- Products with no unit price cannot be sold.
- Money is stored as REAL (per baseline) and rounded to 2 dp using Decimal; no tax/discount/currency.
- Timestamps are UTC (SQLite CURRENT_TIMESTAMP).
- `services.py` added at the root (not in the suggested tree) to keep business logic out of routes.
- Product code is optional/unique; blank is stored as NULL.
- No user-management UI; users are created via `flask create-user`.
- Sale cannot be edited or voided (not in scope).

## 5. Known limitations
- Lists are capped (500 movements, 200 sales); no pagination.
- No login rate limiting / lockout.
- Debug mode must not be used in production; HTTPS cookie flag via `SESSION_COOKIE_SECURE=1`.
- Tested with Flask test client and a live local smoke test; not tested in a real browser or on Windows.
