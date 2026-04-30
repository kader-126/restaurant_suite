# Restaurant Suite (Odoo 19) - Test Scenarios

This document provides practical end-to-end test scenarios to validate the `restaurant_suite` module.

## 1. Scope

The scenarios validate:
- Module installation and data loading
- Security groups and access rights
- Recipe and food cost engine (yield-adjusted)
- Waste reason integration on stock scrap
- KDS backend flow
- PAR replenishment and automatic purchase order generation
- Franchise royalty computation and invoice generation
- KPI backend dashboard data aggregation
- Reports and wizard behavior
- Regression checks (no duplicate native POS behavior)

## 2. Prerequisites

- Odoo 19 instance with modules installed:
  - `point_of_sale`
  - `mrp`
  - `stock`
  - `purchase`
  - `account`
  - `mail`
  - `web`
- `restaurant_suite` installed on a test database
- At least 3 users available:
  - `manager_user` (Restaurant Manager)
  - `kitchen_user` (Kitchen Staff)
  - `franchise_admin_user` (Franchise Administrator)
- At least one POS config in restaurant mode
- Demo or test products available (food items and ingredients)

## 3. Quick Smoke Test (10 minutes)

1. Install module.
- Expected: no traceback, module installs successfully.

2. Verify menus appear.
- Navigate to `Restaurant Suite` top menu.
- Expected submenus:
  - `Operations`: Recipes, PAR Levels, Franchises
  - `Configuration`: Allergens, Waste Reasons, KDS Stations
  - `Reporting`: KPI Dashboard, Kitchen Display

3. Verify base data loaded.
- Open `Configuration > Allergens` and count records.
- Expected: 14 allergens.
- Open `Configuration > Waste Reasons`.
- Expected: 6 waste reasons.

4. Verify scheduled actions.
- Go to `Settings > Technical > Automation > Scheduled Actions`.
- Search `Restaurant Suite`.
- Expected:
  - `Check PAR Levels and Generate POs`
  - `Compute Monthly Franchise Royalties`

If all four pass, continue with full scenarios.

## 4. Detailed Functional Scenarios

## 4.1 Security and Access Rights

### Scenario SEC-01: Manager full access
Steps:
1. Login as `manager_user`.
2. Open each suite model menu and try create/edit/delete where relevant.

Expected:
- Manager can CRUD: allergens, recipes, KDS orders/stations, PAR levels, scrap reasons.
- Manager can read KPI data.

### Scenario SEC-02: Kitchen restricted access
Steps:
1. Login as `kitchen_user`.
2. Open Allergens and Recipes.
3. Try edit/create.
4. Open KDS Orders and try status write.

Expected:
- Kitchen can read allergens/recipes.
- Kitchen cannot create/edit allergens/recipes.
- Kitchen can update KDS order status where allowed by access file.

### Scenario SEC-03: Franchise admin access
Steps:
1. Login as `franchise_admin_user`.
2. Open Franchises menu.
3. Create and edit franchise records.
4. Open royalty wizard from franchise form.

Expected:
- Franchise admin can fully manage franchise and run invoice wizard.

## 4.2 Recipe and Food Cost Engine

### Scenario REC-01: Create recipe and phantom BoM link
Steps:
1. Create POS-sellable dish product template (e.g. `Burger Test`).
2. Create recipe for this product.
3. Click `Create/Open BoM`.

Expected:
- Phantom BoM created and linked if none existed.
- BoM opens in dialog.

### Scenario REC-02: Yield-adjusted cost calculation
Test data:
- Ingredient A standard price = 10.00
- BoM qty = 2.0
- yield_ratio = 1.00
- Ingredient B standard price = 8.00
- BoM qty = 1.0
- yield_ratio = 0.80
- Selling price = 50.00

Manual calculation:
- Cost A = 10 * 2 / 1.00 = 20.00
- Cost B = 8 * 1 / 0.80 = 10.00
- Total bom_cost = 30.00
- Food cost % = 60.00
- Margin = 20.00
- Margin % = 40.00

Steps:
1. Set above values in ingredients and BoM lines.
2. Save recipe.

Expected:
- `bom_cost`, `food_cost_pct`, `margin`, `margin_pct` match expected values.

### Scenario REC-03: Yield ratio constraint
Steps:
1. Edit BoM line `yield_ratio` to 0.00.
2. Save.
3. Edit to 1.20 and save.

Expected:
- ValidationError raised for both invalid values.
- Accepted range: 0.01 to 1.00.

### Scenario REC-04: Recipe reports
Steps:
1. Open recipe.
2. Run `Print Recipe Card`.
3. Run `Print Food Cost`.

Expected:
- Both reports render PDF without traceback.
- Values reflect recipe data.

## 4.3 Waste Reason Integration

### Scenario WST-01: Waste reason on scrap
Steps:
1. Go to inventory scrap operation.
2. Create a scrap for an ingredient.
3. Set `Waste Reason`.
4. Validate scrap.

Expected:
- Scrap saved with `waste_reason_id`.
- Field visible in scrap form.

## 4.4 KDS Backend Flow

### Scenario KDS-01: Station setup
Steps:
1. Create KDS Station with `pos_config_id` and selected POS categories.

Expected:
- Station saves correctly.

### Scenario KDS-02: Send POS order lines to KDS
Steps:
1. Create POS order with lines in configured categories.
2. Call `create_kds_lines(station_id)` (via server action/shell or integrated flow).

Expected:
- KDS records created in `restaurant.kds.order`.
- Related `pos.order.line` updated with `kds_sent=True`, `kds_status='pending'`.

### Scenario KDS-03: Status transitions and order state
Steps:
1. Mark one KDS line as `preparing`.
2. Mark as `ready`.
3. Mark as `served`.
4. Check `pos.order.kds_state` through lifecycle.

Expected:
- KDS line updates correctly.
- Order `kds_state` transitions among `partial/all_sent/ready/served` based on line states.

### Scenario KDS-04: Backend KDS screen
Steps:
1. Open `Reporting > Kitchen Display`.
2. Confirm cards load and refresh every ~10 sec.
3. Use `Prep` and `Ready` buttons.

Expected:
- No JS errors.
- Buttons trigger backend updates and refresh list.
- Urgency class changes by elapsed minutes.

## 4.5 PAR Replenishment

### Scenario PAR-01: Need reorder computed
Test data:
- Product stock at location = 5
- `min_qty` = 10
- `par_qty` = 20

Steps:
1. Create PAR record with supplier.
2. Open record and verify `current_stock` and `needs_reorder`.

Expected:
- `current_stock=5`
- `needs_reorder=True`

### Scenario PAR-02: Generate purchase orders (manual)
Steps:
1. Trigger method `generate_purchase_orders()` manually from shell or scheduled action run.
2. Open generated draft purchase order.

Expected:
- PO created (or reused draft for same supplier/company).
- POL quantity = `par_qty - current_stock`.
- `last_po_date` updated on PAR records.
- PO chatter contains auto-replenishment message.

### Scenario PAR-03: Missing supplier
Steps:
1. Create PAR needing reorder without supplier.
2. Trigger generation.

Expected:
- Record skipped, no PO line created.
- No crash.

## 4.6 Franchise Royalties

### Scenario FRN-01: Revenue period fetch and royalty invoice
Test data:
- POS sales in previous month = 10,000.00
- `royalty_rate` = 5%

Expected amount:
- 500.00

Steps:
1. Configure franchise with company, HQ, account, journal.
2. Run wizard with previous month range.

Expected:
- Vendor bill created in franchise company.
- Partner = HQ partner.
- One line with correct account and amount 500.00.
- Franchise chatter contains message with invoice reference.

### Scenario FRN-02: Missing accounting config
Steps:
1. Remove royalty account or journal.
2. Run royalty computation.

Expected:
- No crash.
- No invoice created.
- Warning behavior in logs.

### Scenario FRN-03: Monthly cron behavior
Steps:
1. Trigger `Compute Monthly Franchise Royalties` scheduled action manually.

Expected:
- Runs for all active franchises.
- Handles exceptions per franchise without stopping entire loop.

## 4.7 KPI Dashboard

### Scenario KPI-01: Dashboard loads and metrics present
Steps:
1. Open `Reporting > KPI Dashboard`.
2. Select date range and presets (`Today`, `Week`, `Month`).

Expected:
- Component loads without JS traceback.
- Cards display: revenue, covers, revenue/cover, food cost %, waste value.
- Top items table populated when data exists.

### Scenario KPI-02: SQL aggregation sanity
Steps:
1. Compare dashboard totals with known POS and scrap data for a short period.

Expected:
- Revenue aligns with POS completed states (`paid`, `done`, `invoiced`).
- Waste value reflects validated scrap cost.
- Daily and hourly series return structured lists.

## 5. Regression and Non-Duplication Checks

### Scenario REG-01: Native POS still controls restaurant operations
Steps:
1. Open POS restaurant session.
2. Check floor plans, table transfer/merge, split bill, course handling.

Expected:
- Native `point_of_sale` features work normally.
- No duplicate `restaurant.floor` or `restaurant.table` models created.

### Scenario REG-02: Native model integrity
Steps:
1. Check Technical > Database Structure > Models and fields.
2. Verify extensions only:
  - `pos.config`: new fields `kds_station_ids`, `franchise_id`
  - `pos.order`: new field `kds_state`
  - `pos.order.line`: new fields `kds_status`, `kds_sent`
  - `stock.scrap`: new field `waste_reason_id`

Expected:
- No duplicate redefinitions of native fields like `table_id`, `covers`, split bill settings.

## 6. Optional Odoo Shell Test Snippets

Use shell carefully on test DB only.

```python
# Open Odoo shell first:
# odoo-bin shell -d <db_name>

# PAR generation
env['restaurant.par.level'].generate_purchase_orders()

# Franchise monthly cron
env['restaurant.franchise'].compute_all_royalties()

# KPI sample
env['restaurant.kpi'].get_dashboard_data('2026-04-01', '2026-04-30')
```

## 7. Exit Criteria (Go/No-Go)

Release candidate is acceptable when all are true:
- All smoke tests pass
- No install/upgrade traceback
- No JS errors in KDS/KPI client actions
- Financial outputs (food cost and royalties) match expected calculations
- PAR creates correct PO quantities
- Security rights behave as designed
- Native POS restaurant features remain unaffected

## 8. Defect Log Template

Use this template for each issue found:

- ID:
- Title:
- Severity: Blocker / High / Medium / Low
- Area: Security / Recipe / KDS / PAR / Franchise / KPI / UI / Report
- Preconditions:
- Steps to Reproduce:
- Expected Result:
- Actual Result:
- Evidence (screenshot/log/traceback):
- Environment (DB/module version/date):
- Status:

## 9. Recommended Test Order

1. Smoke tests
2. Security
3. Recipe + reports
4. Waste integration
5. KDS flow
6. PAR flow
7. Franchise + wizard + cron
8. KPI dashboard
9. Regression checks on native POS

---

If you want, I can also generate a second file with a strict UAT checklist format (checkboxes) so your team can mark pass/fail directly during testing.
