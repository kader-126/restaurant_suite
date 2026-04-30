# `restaurant_suite` — Odoo 19 Module (Revised Architecture)
## GitHub Copilot Development Guide — Extend Native, No Duplication

> **Core principle**: Odoo 19 already ships a mature restaurant POS module.
> This module ONLY adds what is missing: food cost/recipe engine, PAR purchasing,
> franchise royalties, KPI dashboard, and a KDS backend screen.
> Everything POS-side (floors, tables, courses, split bill, preparation printers)
> is inherited and extended — never recreated.

---

## 0. What Odoo 19 Already Has (DO NOT recreate)

Before writing any code, understand what the native `point_of_sale` module
already provides in Odoo 19 so you never duplicate it:

| Native model / feature | Where it lives | What it does |
|---|---|---|
| `pos.floor` | `point_of_sale` addon | Floor plans, background image, linked to pos.config |
| `pos.table` | `point_of_sale` addon | Tables with shape, seats, position, color, active |
| Course management | POS JS (native) | "Course" button in POS, "Fire Course N" per order |
| Bill splitting | POS JS (native) | Native split bill at payment screen |
| Preparation display | POS JS (native) | Kitchen/bar display linked to order printers |
| Allergen tags | `product.template` field | `pos_allergen_ids` many2many on product |
| Table booking | `appointments` addon | Optional integration via pos.config |
| Transfer/Merge | POS JS (native) | Move order from table to table |
| `pos.order` | `point_of_sale` addon | Orders with table_id, covers (Odoo 17+) |
| `pos.order.line` | `point_of_sale` addon | Lines with note field |

**Rule**: If it exists in `point_of_sale`, use `_inherit` to extend it.
Never create `restaurant.floor`, `restaurant.table`, or duplicate course logic.

---

## 1. Module Identity

### `__manifest__.py`

```python
{
    'name': 'Restaurant Suite',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Recipe costing, PAR purchasing, franchise royalties, KPI dashboard',
    'description': """
        Extends Odoo 19 native restaurant POS with:
        - Recipe / Bill of Materials food cost engine (yield-adjusted)
        - PAR-level automatic purchase order generation
        - Franchise royalty computation and vendor bill generation
        - SQL-powered KPI dashboard (revenue, food cost %, waste, top items)
        - Backend KDS screen with urgency colors and line status tracking
        - EU-14 allergen master linked to recipes (extends native product allergens)
        - Waste reason tracking on stock.scrap

        Does NOT recreate: floors, tables, courses, split bill, preparation printers.
        Those are used as-is from the native point_of_sale module.
    """,
    'author': 'Your Name',
    'depends': [
        'point_of_sale',   # native restaurant features live here
        'mrp',             # BoM for recipes
        'stock',           # PAR levels, scrap tracking
        'purchase',        # auto PO generation
        'account',         # royalty invoices
        'mail',            # chatter on recipes and franchises
        'web',             # Owl components
    ],
    'data': [
        'security/restaurant_security.xml',
        'security/ir.model.access.csv',
        'data/restaurant_data.xml',       # EU allergens, waste reasons, crons
        'data/cron_data.xml',
        'views/menus.xml',
        # --- New backend models (not duplicating POS native) ---
        'views/restaurant_allergen_views.xml',
        'views/restaurant_recipe_views.xml',
        'views/restaurant_kds_views.xml',
        'views/par_level_views.xml',
        'views/franchise_views.xml',
        'views/kpi_dashboard_views.xml',
        # --- Extensions of native POS views ---
        'views/pos_config_views_extend.xml',   # add suite settings tab
        'views/stock_scrap_views_extend.xml',  # add waste_reason_id field
        # --- Reports ---
        'report/food_cost_report.xml',
        'report/recipe_card_report.xml',
        # --- Wizards ---
        'wizard/royalty_invoice_wizard_views.xml',
    ],
    'assets': {
        # Backend KDS screen and KPI dashboard (Owl, runs in web client)
        'web.assets_backend': [
            'restaurant_suite/static/src/js/kds_backend.js',
            'restaurant_suite/static/src/js/kpi_dashboard.js',
            'restaurant_suite/static/src/xml/kds_backend.xml',
            'restaurant_suite/static/src/xml/kpi_dashboard.xml',
            'restaurant_suite/static/src/css/restaurant_suite.css',
        ],
    },
    'demo': ['demo/restaurant_demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

> **Notice**: NO `point_of_sale._assets_pos` block.
> We do not patch the POS frontend — the native POS handles floor/table/course UI.
> Our additions are backend screens only.

---

## 2. Module File Structure

```
restaurant_suite/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── restaurant_allergen.py      # NEW model — EU-14 allergen master
│   ├── restaurant_recipe.py        # NEW model — dish recipe + food cost
│   ├── mrp_bom_line.py             # EXTEND mrp.bom.line — yield_ratio field
│   ├── restaurant_kds_order.py     # NEW model — KDS order tracking (backend)
│   ├── par_level.py                # NEW model — PAR level + auto PO cron
│   ├── franchise.py                # NEW model — franchise royalty engine
│   ├── restaurant_kpi.py           # NEW model — SQL KPI aggregation
│   ├── pos_config.py               # EXTEND pos.config — link to suite settings
│   ├── pos_order.py                # EXTEND pos.order — kds_state computed
│   ├── pos_order_line.py           # EXTEND pos.order.line — kds_status, kds_sent
│   ├── stock_scrap.py              # EXTEND stock.scrap — waste_reason_id
│   └── restaurant_scrap_reason.py  # NEW model — waste reason master
├── wizard/
│   ├── __init__.py
│   └── royalty_invoice_wizard.py
├── views/  (one file per model)
├── data/
│   ├── restaurant_data.xml
│   └── cron_data.xml
├── demo/
│   └── restaurant_demo.xml
├── security/
│   ├── restaurant_security.xml
│   └── ir.model.access.csv
├── report/
│   ├── food_cost_report.xml
│   └── recipe_card_report.xml
└── static/src/
    ├── js/
    │   ├── kds_backend.js          # Backend KDS Owl component
    │   └── kpi_dashboard.js        # Backend KPI Owl component
    ├── xml/
    │   ├── kds_backend.xml
    │   └── kpi_dashboard.xml
    └── css/
        └── restaurant_suite.css
```

---

## 3. Security

### `security/restaurant_security.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record id="module_restaurant_suite" model="ir.module.category">
            <field name="name">Restaurant Suite</field>
            <field name="sequence">50</field>
        </record>

        <!-- Kitchen Staff: view-only on suite models -->
        <record id="group_restaurant_kitchen" model="res.groups">
            <field name="name">Kitchen Staff</field>
            <field name="category_id" ref="module_restaurant_suite"/>
        </record>

        <!-- Restaurant Manager: full CRUD on suite models -->
        <record id="group_restaurant_manager" model="res.groups">
            <field name="name">Restaurant Manager</field>
            <field name="category_id" ref="module_restaurant_suite"/>
            <field name="implied_ids" eval="[(4, ref('group_restaurant_kitchen'))]"/>
            <field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
        </record>

        <!-- Franchise Admin: full access including royalties -->
        <record id="group_restaurant_franchise_admin" model="res.groups">
            <field name="name">Franchise Administrator</field>
            <field name="category_id" ref="module_restaurant_suite"/>
            <field name="implied_ids" eval="[(4, ref('group_restaurant_manager'))]"/>
        </record>
    </data>
</odoo>
```

### `security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_allergen_manager,allergen manager,model_restaurant_allergen,group_restaurant_manager,1,1,1,1
access_allergen_kitchen,allergen kitchen,model_restaurant_allergen,group_restaurant_kitchen,1,0,0,0
access_recipe_manager,recipe manager,model_restaurant_recipe,group_restaurant_manager,1,1,1,1
access_recipe_kitchen,recipe kitchen,model_restaurant_recipe,group_restaurant_kitchen,1,0,0,0
access_kds_order_manager,kds manager,model_restaurant_kds_order,group_restaurant_manager,1,1,1,1
access_kds_order_kitchen,kds kitchen,model_restaurant_kds_order,group_restaurant_kitchen,1,1,0,0
access_par_level_manager,par manager,model_restaurant_par_level,group_restaurant_manager,1,1,1,1
access_franchise_admin,franchise admin,model_restaurant_franchise,group_restaurant_franchise_admin,1,1,1,1
access_scrap_reason_manager,scrap reason manager,model_restaurant_scrap_reason,group_restaurant_manager,1,1,1,1
access_kpi_manager,kpi manager,model_restaurant_kpi,group_restaurant_manager,1,0,0,0
```

---

## 4. Setup Data

### `data/restaurant_data.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- noupdate=1: never overwrite after first install -->
<odoo noupdate="1">
    <data>

        <!-- ===== EU 14 ALLERGENS (master data) ===== -->
        <!-- These complement native pos_allergen_ids on product.template -->
        <!-- Use them on restaurant.recipe for dish-level allergen display -->
        <record id="allergen_gluten"      model="restaurant.allergen"><field name="name">Gluten</field><field name="code">GL</field></record>
        <record id="allergen_crustaceans" model="restaurant.allergen"><field name="name">Crustacés</field><field name="code">CR</field></record>
        <record id="allergen_eggs"        model="restaurant.allergen"><field name="name">Oeufs</field><field name="code">OE</field></record>
        <record id="allergen_fish"        model="restaurant.allergen"><field name="name">Poisson</field><field name="code">PO</field></record>
        <record id="allergen_peanuts"     model="restaurant.allergen"><field name="name">Arachides</field><field name="code">AR</field></record>
        <record id="allergen_soy"         model="restaurant.allergen"><field name="name">Soja</field><field name="code">SO</field></record>
        <record id="allergen_milk"        model="restaurant.allergen"><field name="name">Lait / Lactose</field><field name="code">LA</field></record>
        <record id="allergen_nuts"        model="restaurant.allergen"><field name="name">Fruits à coque</field><field name="code">FC</field></record>
        <record id="allergen_celery"      model="restaurant.allergen"><field name="name">Céleri</field><field name="code">CE</field></record>
        <record id="allergen_mustard"     model="restaurant.allergen"><field name="name">Moutarde</field><field name="code">MO</field></record>
        <record id="allergen_sesame"      model="restaurant.allergen"><field name="name">Sésame</field><field name="code">SE</field></record>
        <record id="allergen_sulphites"   model="restaurant.allergen"><field name="name">Sulfites / SO2</field><field name="code">SU</field></record>
        <record id="allergen_lupin"       model="restaurant.allergen"><field name="name">Lupin</field><field name="code">LU</field></record>
        <record id="allergen_molluscs"    model="restaurant.allergen"><field name="name">Mollusques</field><field name="code">MO2</field></record>

        <!-- ===== WASTE REASONS ===== -->
        <record id="waste_expired"       model="restaurant.scrap.reason"><field name="name">Produit périmé</field><field name="code">EXPIRED</field></record>
        <record id="waste_prep"          model="restaurant.scrap.reason"><field name="name">Perte de préparation</field><field name="code">PREP</field></record>
        <record id="waste_cooking"       model="restaurant.scrap.reason"><field name="name">Erreur de cuisson</field><field name="code">COOK</field></record>
        <record id="waste_customer"      model="restaurant.scrap.reason"><field name="name">Retour client</field><field name="code">RETURN</field></record>
        <record id="waste_overproduction"model="restaurant.scrap.reason"><field name="name">Surproduction</field><field name="code">OVER</field></record>
        <record id="waste_storage"       model="restaurant.scrap.reason"><field name="name">Mauvais stockage</field><field name="code">STORAGE</field></record>

    </data>
</odoo>
```

### `data/cron_data.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record id="cron_par_level_check" model="ir.cron">
            <field name="name">Restaurant Suite: Check PAR Levels and Generate POs</field>
            <field name="model_id" ref="model_restaurant_par_level"/>
            <field name="state">code</field>
            <field name="code">model.generate_purchase_orders()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="numbercall">-1</field>
            <field name="active">True</field>
        </record>

        <record id="cron_royalty_compute" model="ir.cron">
            <field name="name">Restaurant Suite: Compute Monthly Franchise Royalties</field>
            <field name="model_id" ref="model_restaurant_franchise"/>
            <field name="state">code</field>
            <field name="code">model.compute_all_royalties()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">months</field>
            <field name="numbercall">-1</field>
            <field name="active">True</field>
        </record>
    </data>
</odoo>
```

---

## 5. Models — New (no overlap with native)

### 5.1 `models/restaurant_allergen.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.allergen.
#  Fields: name (Char, required, translate), code (Char, size=5), description (Text),
#  icon (Binary), active (Boolean default True).
#  SQL unique constraint on code.
#  This is a MASTER TABLE — not the same as the native pos allergen tags on product.
#  The native tags handle per-product display in POS.
#  This model handles per-RECIPE allergen declaration for food cost reports."

from odoo import models, fields

class RestaurantAllergen(models.Model):
    _name = 'restaurant.allergen'
    _description = 'Food Allergen — EU Regulation 1169/2011'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(size=5)
    description = fields.Text(translate=True)
    icon = fields.Binary()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Allergen code must be unique.'),
    ]
```

### 5.2 `models/restaurant_scrap_reason.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.scrap.reason.
#  Fields: name (Char, required), code (Char, size=10, unique), active Boolean.
#  This categorizes waste in stock.scrap for waste value KPI computation."

from odoo import models, fields

class RestaurantScrapReason(models.Model):
    _name = 'restaurant.scrap.reason'
    _description = 'Restaurant Waste / Scrap Reason'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(size=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Reason code must be unique.'),
    ]
```

### 5.3 `models/restaurant_recipe.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.recipe.
#  Links product.template to a phantom mrp.bom for food cost calculation.
#  Fields:
#    product_id: Many2one product.template (required, domain available_in_pos=True)
#    bom_id: Many2one mrp.bom (domain product_tmpl_id=product_id, type=phantom)
#    allergen_ids: Many2many restaurant.allergen
#    preparation_time: Integer (minutes)
#    cooking_time: Integer (minutes)
#    method: Html (plating instructions)
#    image: Image
#    active: Boolean default True
#    company_id: Many2one res.company default env.company
#    selling_price: Float related to product_id.list_price readonly
#    bom_cost: Float computed stored — see _compute_bom_cost
#    food_cost_pct: Float computed stored
#    margin: Float computed stored
#    margin_pct: Float computed stored
#
#  _compute_bom_cost:
#    For each bom_line in bom_id.bom_line_ids:
#      cost += line.product_id.standard_price * line.product_qty / max(line.yield_ratio, 0.01)
#    bom_cost = cost
#    food_cost_pct = bom_cost / selling_price * 100 if selling_price else 0
#    margin = selling_price - bom_cost
#    margin_pct = margin / selling_price * 100 if selling_price else 0
#
#  action_create_bom(): create phantom BoM if none, open in dialog
#  action_print_recipe_card(): return report action
#  Inherit mail.thread and mail.activity.mixin."

from odoo import models, fields, api

class RestaurantRecipe(models.Model):
    _name = 'restaurant.recipe'
    _description = 'Dish Recipe with Food Cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(related='product_id.name', store=True, readonly=False)
    product_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade',
        domain=[('available_in_pos', '=', True)],
    )
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Materials',
        domain="[('product_tmpl_id', '=', product_id), ('type', '=', 'phantom')]",
    )
    allergen_ids = fields.Many2many(
        'restaurant.allergen', string='Allergens (Recipe Level)',
        relation='recipe_allergen_rel', column1='recipe_id', column2='allergen_id',
        help='Allergens present in this recipe. Separate from per-product POS allergen tags.',
    )
    preparation_time = fields.Integer(string='Prep Time (min)', default=15)
    cooking_time = fields.Integer(string='Cooking Time (min)', default=20)
    method = fields.Html(string='Method / Plating Notes', translate=True, sanitize=False)
    image = fields.Image(string='Recipe Photo')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    selling_price = fields.Float(related='product_id.list_price', readonly=True)
    bom_cost = fields.Float(compute='_compute_bom_cost', store=True, digits='Product Price')
    food_cost_pct = fields.Float(compute='_compute_bom_cost', store=True, digits=(5, 2))
    margin = fields.Float(compute='_compute_bom_cost', store=True, digits='Product Price')
    margin_pct = fields.Float(compute='_compute_bom_cost', store=True, digits=(5, 2))

    @api.depends(
        'bom_id', 'bom_id.bom_line_ids', 'bom_id.bom_line_ids.product_id',
        'bom_id.bom_line_ids.product_qty', 'bom_id.bom_line_ids.yield_ratio',
        'bom_id.bom_line_ids.product_id.standard_price', 'product_id.list_price',
    )
    def _compute_bom_cost(self):
        """
        Yield-adjusted food cost:
          cost = SUM( std_price * qty / yield_ratio ) for each BoM line
        yield_ratio must be 0.01..1.0 — set on mrp.bom.line via our extension.
        """
        for rec in self:
            cost = 0.0
            if rec.bom_id:
                for line in rec.bom_id.bom_line_ids:
                    ratio = max(line.yield_ratio, 0.01)
                    cost += line.product_id.standard_price * line.product_qty / ratio
            rec.bom_cost = cost
            price = rec.selling_price or 0.0
            rec.food_cost_pct = (cost / price * 100.0) if price else 0.0
            rec.margin = price - cost
            rec.margin_pct = ((price - cost) / price * 100.0) if price else 0.0

    def action_create_bom(self):
        """Create a phantom BoM for this product if none exists, then open it."""
        self.ensure_one()
        if not self.bom_id:
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.product_id.id,
                'type': 'phantom',
                'company_id': self.company_id.id,
            })
            self.bom_id = bom
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'res_id': self.bom_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_recipe_card(self):
        return self.env.ref('restaurant_suite.action_recipe_card_report').report_action(self)

    def action_print_food_cost(self):
        return self.env.ref('restaurant_suite.action_food_cost_report').report_action(self)
```

### 5.4 `models/restaurant_kds_order.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.kds.order.
#  This is the BACKEND KDS tracking model — not a POS screen patch.
#  It mirrors pos.order.line status for the backend KDS Owl component.
#
#  Fields:
#    pos_order_line_id: Many2one pos.order.line (required, ondelete cascade)
#    pos_order_id: Many2one pos.order related to pos_order_line_id.order_id stored
#    table_id: Many2one pos.table related to pos_order_id.table_id stored (native pos.table)
#    product_id: Many2one product.product related stored
#    qty: Float related stored
#    note: Char related stored (native note field on pos.order.line)
#    kitchen_status: Selection (pending/preparing/ready/served) default pending
#    sent_at: Datetime (when the line was sent)
#    station_id: Many2one restaurant.kds.station
#    covers: Integer related to pos_order_id.covers stored
#
#  Methods:
#    action_mark_preparing(): write kitchen_status = 'preparing'
#    action_mark_ready(): write kitchen_status = 'ready', call _notify_pos_if_order_complete()
#    action_mark_served(): write kitchen_status = 'served'
#    _notify_pos_if_order_complete(order): if all KDS lines of the order are ready/served,
#      send bus message 'kitchen.order.ready' on channel pos.order.<id>
#
#  @api.model get_pending_for_station(station_id):
#    Return all KDS lines for that station with status in (pending, preparing),
#    grouped by order, sorted by sent_at asc.
#    Returns list of dicts for Owl component.

from odoo import models, fields, api
from datetime import datetime

class RestaurantKdsOrder(models.Model):
    _name = 'restaurant.kds.order'
    _description = 'KDS Backend Order Line Tracking'
    _order = 'sent_at asc'

    pos_order_line_id = fields.Many2one(
        'pos.order.line', required=True, ondelete='cascade', index=True,
    )
    pos_order_id = fields.Many2one(
        'pos.order', related='pos_order_line_id.order_id', store=True,
    )
    table_id = fields.Many2one(
        'pos.table',  # native Odoo 19 model — NOT restaurant.table
        related='pos_order_id.table_id', store=True,
    )
    product_id = fields.Many2one(
        'product.product', related='pos_order_line_id.product_id', store=True,
    )
    qty = fields.Float(related='pos_order_line_id.qty', store=True)
    note = fields.Char(related='pos_order_line_id.note', store=True)
    covers = fields.Integer(related='pos_order_id.covers', store=True)
    station_id = fields.Many2one('restaurant.kds.station', string='Kitchen Station', index=True)
    sent_at = fields.Datetime(default=lambda self: datetime.now())
    kitchen_status = fields.Selection([
        ('pending', 'Pending'),
        ('preparing', 'In Preparation'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ], default='pending', index=True)

    def action_mark_preparing(self):
        self.write({'kitchen_status': 'preparing'})

    def action_mark_ready(self):
        self.write({'kitchen_status': 'ready'})
        for rec in self:
            rec._notify_pos_if_order_complete(rec.pos_order_id)

    def action_mark_served(self):
        self.write({'kitchen_status': 'served'})

    def _notify_pos_if_order_complete(self, order):
        """Send bus notification when all KDS lines for an order are ready/served."""
        kds_lines = self.search([
            ('pos_order_id', '=', order.id),
            ('kitchen_status', 'not in', ['ready', 'served']),
        ])
        if not kds_lines:
            self.env['bus.bus']._sendone(
                f'pos.order.{order.id}',
                'kitchen.order.ready',
                {'order_id': order.id, 'order_name': order.name},
            )

    @api.model
    def get_pending_for_station(self, station_id):
        """
        Called by the backend KDS Owl component via RPC.
        Returns orders with pending/preparing lines for the given station,
        sorted by sent_at (oldest = most urgent).
        """
        lines = self.search([
            ('station_id', '=', station_id),
            ('kitchen_status', 'in', ['pending', 'preparing']),
        ], order='sent_at asc')

        orders = {}
        for line in lines:
            oid = line.pos_order_id.id
            if oid not in orders:
                orders[oid] = {
                    'order_id': oid,
                    'order_name': line.pos_order_id.name,
                    'table_name': line.table_id.name if line.table_id else 'Takeaway',
                    'covers': line.covers,
                    'sent_at': line.sent_at.isoformat() if line.sent_at else None,
                    'lines': [],
                }
            orders[oid]['lines'].append({
                'kds_id': line.id,
                'product_name': line.product_id.name,
                'qty': line.qty,
                'note': line.note or '',
                'kitchen_status': line.kitchen_status,
            })
        return list(orders.values())


class RestaurantKdsStation(models.Model):
    _name = 'restaurant.kds.station'
    _description = 'Backend KDS Station'
    _order = 'name'

    name = fields.Char(required=True)
    pos_category_ids = fields.Many2many(
        'pos.category', string='POS Product Categories',
        help='Orders with products in these categories are routed to this station.',
    )
    display_mode = fields.Selection([
        ('ticket', 'Ticket View'),
        ('grid', 'Grid View'),
    ], default='ticket')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
```

### 5.5 `models/par_level.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.par.level.
#  Fields:
#    product_id: Many2one product.product (required)
#    location_id: Many2one stock.location (required, domain usage=internal)
#    par_qty: Float (target stock level)
#    min_qty: Float (reorder point — trigger PO when stock < this)
#    uom_id: Many2one uom.uom (related to product uom_po_id)
#    supplier_id: Many2one res.partner (preferred supplier)
#    lead_time: Integer (days, default 1)
#    last_po_date: Date (readonly)
#    active: Boolean default True
#    company_id: Many2one res.company
#    current_stock: Float computed (not stored) via _get_current_stock()
#    needs_reorder: Boolean computed (current_stock < min_qty)
#
#  _get_current_stock(): sum stock.quant quantity for product+location
#
#  generate_purchase_orders() [@api.model, cron entry]:
#    - Loop all active PAR records
#    - For each where _get_current_stock() < min_qty:
#        order_qty = par_qty - current_stock
#        group by (supplier_id, company_id)
#    - For each group: create/update draft purchase.order + purchase.order.line
#    - Fetch supplier price from product.supplierinfo if available
#    - Post message on PO
#    - Write last_po_date = today
#    - Log count via _logger
#
#  _create_purchase_order(supplier_id, company_id, par_records): helper"

from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class ParLevel(models.Model):
    _name = 'restaurant.par.level'
    _description = 'PAR Level — Periodic Automatic Replenishment'
    _order = 'location_id, product_id'

    product_id = fields.Many2one('product.product', required=True, ondelete='cascade', index=True)
    location_id = fields.Many2one(
        'stock.location', required=True, ondelete='cascade',
        domain=[('usage', '=', 'internal')],
    )
    par_qty = fields.Float(string='PAR Quantity', digits='Product Unit of Measure')
    min_qty = fields.Float(string='Reorder Point', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_po_id', readonly=True)
    supplier_id = fields.Many2one('res.partner', domain=[('supplier_rank', '>', 0)])
    lead_time = fields.Integer(string='Lead Time (days)', default=1)
    last_po_date = fields.Date(readonly=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    current_stock = fields.Float(compute='_compute_current_stock', store=False)
    needs_reorder = fields.Boolean(compute='_compute_current_stock', store=False)

    def _compute_current_stock(self):
        for rec in self:
            stock = rec._get_current_stock()
            rec.current_stock = stock
            rec.needs_reorder = stock < rec.min_qty

    def _get_current_stock(self):
        self.ensure_one()
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
        ])
        return sum(quants.mapped('quantity'))

    @api.model
    def generate_purchase_orders(self):
        records = self.search([('active', '=', True)])
        to_reorder = [r for r in records if r._get_current_stock() < r.min_qty]
        if not to_reorder:
            _logger.info('PAR cron: no reorders needed.')
            return

        groups = {}
        for rec in to_reorder:
            key = (rec.supplier_id.id or 0, rec.company_id.id)
            groups.setdefault(key, []).append(rec)

        for (supplier_id, company_id), recs in groups.items():
            if not supplier_id:
                _logger.warning('PAR: no supplier for %s — skipped.', [r.product_id.name for r in recs])
                continue
            self._create_purchase_order(supplier_id, company_id, recs)

        self.env['restaurant.par.level'].search([
            ('id', 'in', [r.id for r in to_reorder])
        ]).write({'last_po_date': date.today()})
        _logger.info('PAR cron: processed %d product(s).', len(to_reorder))

    def _create_purchase_order(self, supplier_id, company_id, par_records):
        po = self.env['purchase.order'].create({
            'partner_id': supplier_id,
            'company_id': company_id,
            'notes': 'Auto-generated by Restaurant Suite PAR replenishment.',
        })
        for rec in par_records:
            current = rec._get_current_stock()
            order_qty = rec.par_qty - current
            if order_qty <= 0:
                continue
            supplierinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', supplier_id),
                ('product_id', '=', rec.product_id.id),
            ], limit=1)
            price = supplierinfo.price if supplierinfo else rec.product_id.standard_price
            self.env['purchase.order.line'].create({
                'order_id': po.id,
                'product_id': rec.product_id.id,
                'product_qty': order_qty,
                'product_uom': rec.uom_id.id,
                'price_unit': price,
                'date_planned': fields.Datetime.now(),
                'name': rec.product_id.name,
            })
        po.message_post(body=f'PAR auto-replenishment: {len(par_records)} product(s) below minimum.')
        return po
```

### 5.6 `models/franchise.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.franchise (inherit mail.thread).
#  Fields:
#    name: Char required
#    active: Boolean default True
#    company_id: Many2one res.company (the franchise branch)
#    hq_company_id: Many2one res.company (HQ receiving royalties)
#    hq_partner_id: Many2one res.partner related to hq_company_id.partner_id readonly
#    royalty_rate: Float default 5.0
#    royalty_base: Selection [('revenue','Gross Revenue'),('profit','Net Profit')] default revenue
#    royalty_account_id: Many2one account.account company_dependent
#    royalty_journal_id: Many2one account.journal company_dependent
#
#  _get_period_revenue(date_from, date_to):
#    SQL: SUM pos_order.amount_total WHERE company_id=self.company_id,
#    state IN (paid,done,invoiced), date_order BETWEEN date_from AND date_to
#    Returns float.
#
#  compute_monthly_royalty(date_from, date_to):
#    revenue = _get_period_revenue(date_from, date_to)
#    royalty_amount = revenue * royalty_rate / 100
#    if royalty_amount <= 0: log and return False
#    Create account.move (in_invoice) in self.company_id with:
#      partner_id = hq_partner_id
#      journal_id = royalty_journal_id
#      invoice_date = date_to
#      ref = 'Royalty {date_from} -> {date_to}'
#      line: account=royalty_account_id, qty=1, price=royalty_amount,
#            name='Franchise royalty {rate}% ...'
#    Post message on franchise record.
#    Return invoice.
#
#  @api.model compute_all_royalties():
#    date_to = first day of current month
#    date_from = first day of previous month
#    Loop all active franchises, call compute_monthly_royalty, catch exceptions."

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class RestaurantFranchise(models.Model):
    _name = 'restaurant.franchise'
    _description = 'Franchise Royalty Configuration'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, string='Franchise Branch Company')
    hq_company_id = fields.Many2one('res.company', required=True, string='HQ Company')
    hq_partner_id = fields.Many2one('res.partner', related='hq_company_id.partner_id', readonly=True)
    royalty_rate = fields.Float(default=5.0, digits=(5, 2))
    royalty_base = fields.Selection([
        ('revenue', 'Gross Revenue (POS Sales)'),
        ('profit', 'Net Profit'),
    ], default='revenue', required=True)
    royalty_account_id = fields.Many2one(
        'account.account', company_dependent=True,
        domain=[('account_type', 'in', ('expense', 'expense_direct_cost'))],
    )
    royalty_journal_id = fields.Many2one(
        'account.journal', company_dependent=True,
        domain=[('type', 'in', ('purchase', 'general'))],
    )

    def _get_period_revenue(self, date_from, date_to):
        self.ensure_one()
        self.env.cr.execute("""
            SELECT COALESCE(SUM(amount_total), 0)
            FROM pos_order
            WHERE state IN ('paid', 'done', 'invoiced')
              AND company_id = %s
              AND date_order::date >= %s
              AND date_order::date < %s
        """, (self.company_id.id, date_from, date_to))
        return float(self.env.cr.fetchone()[0] or 0)

    def compute_monthly_royalty(self, date_from, date_to):
        self.ensure_one()
        revenue = self._get_period_revenue(date_from, date_to)
        amount = revenue * self.royalty_rate / 100.0
        if amount <= 0:
            _logger.info('Franchise %s: no revenue %s-%s', self.name, date_from, date_to)
            return False
        invoice = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'in_invoice',
            'partner_id': self.hq_partner_id.id,
            'company_id': self.company_id.id,
            'journal_id': self.royalty_journal_id.id,
            'invoice_date': date_to,
            'ref': f'Royalty {date_from} > {date_to}',
            'invoice_line_ids': [(0, 0, {
                'name': f'Royalty {self.royalty_rate}% on {self.royalty_base} ({date_from} > {date_to})',
                'account_id': self.royalty_account_id.id,
                'quantity': 1.0,
                'price_unit': amount,
            })],
        })
        self.message_post(body=f'Royalty invoice {invoice.name}: {amount:.2f} EUR.')
        return invoice

    @api.model
    def compute_all_royalties(self):
        today = date.today()
        date_to = today.replace(day=1)
        date_from = date_to - relativedelta(months=1)
        for franchise in self.search([('active', '=', True)]):
            try:
                franchise.compute_monthly_royalty(date_from, date_to)
            except Exception as e:
                _logger.error('Royalty error for %s: %s', franchise.name, e)
```

### 5.7 `models/restaurant_kpi.py`

```python
# Copilot prompt:
# "Create Odoo 19 model restaurant.kpi (_auto=False, no real table).
#  All methods are @api.model, all computation via direct SQL for performance.
#
#  get_dashboard_data(date_from, date_to, company_id=None):
#    Returns dict with:
#      revenue: float — SUM pos_order.amount_total WHERE state in paid/done/invoiced
#      covers: int — SUM pos_order.covers (native Odoo 17+ field)
#      orders: int — COUNT pos_order.id
#      revenue_per_cover: float — revenue/covers
#      food_cost: float — from _compute_total_food_cost()
#      food_cost_pct: float — food_cost/revenue*100
#      waste_value: float — from _compute_waste_value()
#      top_items: list — from _get_top_items() top 10 by revenue
#      hourly_revenue: list {hour, revenue} — from _get_hourly_curve()
#      daily_revenue: list {date, revenue} — from _get_daily_revenue()
#
#  _compute_total_food_cost(date_from, date_to, company_id):
#    JOIN pos_order_line -> mrp_bom (phantom) -> mrp_bom_line -> product
#    SUM qty_sold * bom_line.product_qty / NULLIF(yield_ratio,0) * std_price
#
#  _compute_waste_value(date_from, date_to, company_id):
#    JOIN stock_scrap -> product_template
#    SUM scrap_qty * standard_price WHERE state=done AND date in range
#
#  _get_top_items(date_from, date_to, company_id, limit=10):
#    GROUP BY product, SUM qty, SUM revenue, AVG price, AVG std_cost
#    Returns list of dicts: name, qty, revenue, avg_price, std_cost, margin
#
#  _get_hourly_curve(date_from, date_to, company_id):
#    EXTRACT(HOUR FROM date_order AT TIME ZONE 'Europe/Paris')
#    GROUP BY hour, SUM revenue
#
#  _get_daily_revenue(date_from, date_to, company_id):
#    GROUP BY date_order::date, SUM amount_total"

from odoo import models, fields, api

class RestaurantKPI(models.Model):
    _name = 'restaurant.kpi'
    _description = 'Restaurant KPI Engine'
    _auto = False

    @api.model
    def get_dashboard_data(self, date_from, date_to, company_id=None):
        cf = 'AND company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(f"""
            SELECT COALESCE(SUM(amount_total),0), COALESCE(SUM(covers),0), COUNT(id)
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {cf}
        """, p)
        rev, covers, orders = self.env.cr.fetchone()
        rev = float(rev); covers = int(covers); orders = int(orders)
        food_cost = self._compute_total_food_cost(date_from, date_to, company_id)
        waste = self._compute_waste_value(date_from, date_to, company_id)
        return {
            'revenue': round(rev, 2),
            'covers': covers,
            'orders': orders,
            'revenue_per_cover': round(rev / covers, 2) if covers else 0,
            'food_cost': round(food_cost, 2),
            'food_cost_pct': round(food_cost / rev * 100, 1) if rev else 0,
            'waste_value': round(waste, 2),
            'top_items': self._get_top_items(date_from, date_to, company_id),
            'hourly_revenue': self._get_hourly_curve(date_from, date_to, company_id),
            'daily_revenue': self._get_daily_revenue(date_from, date_to, company_id),
        }

    def _compute_total_food_cost(self, date_from, date_to, company_id=None):
        cf = 'AND po.company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else [])
        self.env.cr.execute(f"""
            SELECT COALESCE(SUM(
                pol.qty * mbl.product_qty / NULLIF(mbl.yield_ratio, 0) * pp.standard_price
            ), 0)
            FROM pos_order_line pol
            JOIN pos_order po ON po.id = pol.order_id
            JOIN mrp_bom mb ON mb.product_tmpl_id = pol.product_id
                           AND mb.type = 'phantom' AND mb.active = true
            JOIN mrp_bom_line mbl ON mbl.bom_id = mb.id
            JOIN product_product pp ON pp.id = mbl.product_id
            WHERE po.state IN ('paid','done','invoiced')
              AND po.date_order::date >= %s AND po.date_order::date <= %s {cf}
        """, p)
        return float(self.env.cr.fetchone()[0] or 0)

    def _compute_waste_value(self, date_from, date_to, company_id=None):
        cf = 'AND ss.company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else [])
        self.env.cr.execute(f"""
            SELECT COALESCE(SUM(ss.scrap_qty * pt.standard_price), 0)
            FROM stock_scrap ss
            JOIN product_product pp ON pp.id = ss.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE ss.state = 'done'
              AND ss.date_done::date >= %s AND ss.date_done::date <= %s {cf}
        """, p)
        return float(self.env.cr.fetchone()[0] or 0)

    def _get_top_items(self, date_from, date_to, company_id=None, limit=10):
        cf = 'AND po.company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else []) + [limit]
        self.env.cr.execute(f"""
            SELECT pt.name->>'en_US', SUM(pol.qty), SUM(pol.price_subtotal),
                   AVG(pol.price_unit), AVG(pt.standard_price)
            FROM pos_order_line pol
            JOIN pos_order po ON po.id = pol.order_id
            JOIN product_product pp ON pp.id = pol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE po.state IN ('paid','done','invoiced')
              AND po.date_order::date >= %s AND po.date_order::date <= %s {cf}
            GROUP BY pt.name ORDER BY SUM(pol.price_subtotal) DESC LIMIT %s
        """, p)
        return [{'name': r[0], 'qty': round(float(r[1] or 0), 1),
                 'revenue': round(float(r[2] or 0), 2),
                 'avg_price': round(float(r[3] or 0), 2),
                 'std_cost': round(float(r[4] or 0), 2),
                 'margin': round(float(r[3] or 0) - float(r[4] or 0), 2)}
                for r in self.env.cr.fetchall()]

    def _get_hourly_curve(self, date_from, date_to, company_id=None):
        cf = 'AND company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else [])
        self.env.cr.execute(f"""
            SELECT EXTRACT(HOUR FROM date_order AT TIME ZONE 'Europe/Paris')::int,
                   COALESCE(SUM(amount_total), 0)
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {cf}
            GROUP BY 1 ORDER BY 1
        """, p)
        return [{'hour': r[0], 'revenue': round(float(r[1]), 2)} for r in self.env.cr.fetchall()]

    def _get_daily_revenue(self, date_from, date_to, company_id=None):
        cf = 'AND company_id = %s' if company_id else ''
        p = [date_from, date_to] + ([company_id] if company_id else [])
        self.env.cr.execute(f"""
            SELECT date_order::date, COALESCE(SUM(amount_total), 0)
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {cf}
            GROUP BY 1 ORDER BY 1
        """, p)
        return [{'date': str(r[0]), 'revenue': round(float(r[1]), 2)} for r in self.env.cr.fetchall()]
```

---

## 6. Models — Extend Native (no recreation)

### 6.1 `models/mrp_bom_line.py`

```python
# Copilot prompt:
# "Extend mrp.bom.line in Odoo 19 with:
#   yield_ratio: Float default 1.0 — ratio of usable ingredient after preparation
#   waste_reason: Char — explanation of the yield loss
#   Constraint: yield_ratio must be between 0.01 and 1.0
#   Help text: '1kg raw -> 0.80kg usable = 0.80. Used in restaurant_suite food cost.'"

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    yield_ratio = fields.Float(
        string='Yield Ratio', default=1.0, digits=(5, 4),
        help='Ratio of usable vs raw quantity after prep. 1=no loss. 0.80=20% waste.',
    )
    waste_reason = fields.Char(string='Waste Reason', help='e.g. peeling, trimming, cooking loss')

    @api.constrains('yield_ratio')
    def _check_yield_ratio(self):
        for line in self:
            if not (0.01 <= line.yield_ratio <= 1.0):
                raise ValidationError(
                    f'Yield ratio for "{line.product_id.name}" must be between 0.01 and 1.0.'
                )
```

### 6.2 `models/pos_config.py`

```python
# Copilot prompt:
# "Extend pos.config in Odoo 19 — inherit only, do NOT redefine existing fields.
#  Add ONLY fields that do not exist natively:
#    kds_station_ids: One2many restaurant.kds.station (suite KDS stations)
#    franchise_id: Many2one restaurant.franchise
#  DO NOT add iface_table_management, iface_split_bill, iface_kds —
#  those are native in Odoo 19 pos.config already."

from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Link to suite KDS stations (backend KDS screen)
    kds_station_ids = fields.One2many(
        'restaurant.kds.station', 'pos_config_id',
        string='KDS Stations (Restaurant Suite)',
    )
    franchise_id = fields.Many2one(
        'restaurant.franchise',
        string='Franchise Config',
        help='Link this POS to a franchise for royalty computation.',
    )
```

> **Note**: Add `pos_config_id` field on `restaurant.kds.station` accordingly.

### 6.3 `models/pos_order.py`

```python
# Copilot prompt:
# "Extend pos.order in Odoo 19.
#  Check first: does pos.order already have a 'covers' field in Odoo 17/18/19?
#  If yes, do NOT redefine it.
#  Add ONLY:
#    kds_state: Selection computed stored
#      (idle/partial/all_sent/ready/served) based on restaurant.kds.order lines
#    Compute: kds_state depends on restaurant.kds.order records for this order.
#
#  Method: create_kds_lines(station_id):
#    For each order line that does not yet have a restaurant.kds.order,
#    check if line.product_id.pos_category_id is in station.pos_category_ids,
#    create restaurant.kds.order with sent_at=now, status=pending."

from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    kds_state = fields.Selection([
        ('idle', 'No items sent to KDS'),
        ('partial', 'Some items in kitchen'),
        ('all_sent', 'All items sent'),
        ('ready', 'All items ready'),
        ('served', 'Fully served'),
    ], compute='_compute_kds_state', store=True, string='KDS State')

    @api.depends('lines')
    def _compute_kds_state(self):
        for order in self:
            kds_lines = self.env['restaurant.kds.order'].search([
                ('pos_order_id', '=', order.id)
            ])
            if not kds_lines:
                order.kds_state = 'idle'
                continue
            all_lines = order.lines
            sent_count = len(kds_lines)
            if sent_count < len(all_lines):
                order.kds_state = 'partial'
            elif all(l.kitchen_status == 'served' for l in kds_lines):
                order.kds_state = 'served'
            elif all(l.kitchen_status in ('ready', 'served') for l in kds_lines):
                order.kds_state = 'ready'
            else:
                order.kds_state = 'all_sent'

    def create_kds_lines(self, station_id):
        """
        Called from the KDS backend when an order is sent.
        Creates restaurant.kds.order records for lines matching the station.
        """
        self.ensure_one()
        station = self.env['restaurant.kds.station'].browse(station_id)
        existing_line_ids = self.env['restaurant.kds.order'].search([
            ('pos_order_id', '=', self.id)
        ]).mapped('pos_order_line_id').ids

        for line in self.lines:
            if line.id in existing_line_ids:
                continue
            if station.pos_category_ids and \
               line.product_id.pos_category_id not in station.pos_category_ids:
                continue
            self.env['restaurant.kds.order'].create({
                'pos_order_line_id': line.id,
                'station_id': station.id,
                'sent_at': fields.Datetime.now(),
                'kitchen_status': 'pending',
            })
```

### 6.4 `models/stock_scrap.py`

```python
# Copilot prompt:
# "Extend stock.scrap in Odoo 19.
#  Add ONE field only:
#    waste_reason_id: Many2one restaurant.scrap.reason
#  This allows filtering waste by reason in the KPI waste_value computation."

from odoo import models, fields

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    waste_reason_id = fields.Many2one(
        'restaurant.scrap.reason',
        string='Waste Reason',
        help='Restaurant Suite: categorizes the reason for this scrap.',
    )
```

---

## 7. Frontend — Backend Owl Components Only

> **Key decision**: We do NOT patch the POS frontend JS.
> The native POS already handles floors, tables, courses, split bill.
> Our two Owl components run in the BACKEND web client only.

### 7.1 `static/src/js/kds_backend.js`

```javascript
/** @odoo-module **/
// Copilot prompt:
// "Create an Odoo 19 Owl backend component RestaurantKDSBackend.
//  Registered as a web.client_action under tag 'restaurant_suite.kds_backend'.
//  Props: stationId (Number).
//  setup():
//    - orm = useService('orm')
//    - notification = useService('notification')
//    - state = useState({ orders: [], stationName: '', lastRefresh: null })
//    - onMounted: load station name, start polling interval (10s)
//    - onWillUnmount: clear interval
//  loadStation(): read restaurant.kds.station name
//  refreshOrders(): call restaurant.kds.order get_pending_for_station(stationId)
//  markPreparing(kdsId): call restaurant.kds.order action_mark_preparing on [kdsId]
//  markReady(kdsId): call restaurant.kds.order action_mark_ready on [kdsId]
//  getElapsedMinutes(sentAt): return minutes since sentAt
//  getUrgency(sentAt): 'normal' | 'warning' (>10min) | 'urgent' (>20min)
//  Template: restaurant_suite.KDSBackend (in kds_backend.xml)"

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class RestaurantKDSBackend extends Component {
    static template = "restaurant_suite.KDSBackend";
    static props = { stationId: { type: Number, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            orders: [],
            stationName: "",
            lastRefresh: null,
            loading: true,
        });
        this._interval = null;

        onMounted(async () => {
            await this.loadStation();
            await this.refreshOrders();
            this._interval = setInterval(() => this.refreshOrders(), 10000);
        });

        onWillUnmount(() => {
            if (this._interval) clearInterval(this._interval);
        });
    }

    async loadStation() {
        if (!this.props.stationId) return;
        const [station] = await this.orm.read(
            "restaurant.kds.station",
            [this.props.stationId],
            ["name"]
        );
        this.state.stationName = station.name;
    }

    async refreshOrders() {
        if (!this.props.stationId) return;
        const orders = await this.orm.call(
            "restaurant.kds.order",
            "get_pending_for_station",
            [[], this.props.stationId]
        );
        this.state.orders = orders;
        this.state.lastRefresh = new Date().toLocaleTimeString();
        this.state.loading = false;
    }

    async markPreparing(kdsId) {
        await this.orm.call("restaurant.kds.order", "action_mark_preparing", [[kdsId]]);
        await this.refreshOrders();
    }

    async markReady(kdsId) {
        await this.orm.call("restaurant.kds.order", "action_mark_ready", [[kdsId]]);
        this.notification.add("Ready!", { type: "success", duration: 2000 });
        await this.refreshOrders();
    }

    getElapsedMinutes(sentAt) {
        if (!sentAt) return 0;
        return Math.floor((Date.now() - new Date(sentAt).getTime()) / 60000);
    }

    getUrgency(sentAt) {
        const min = this.getElapsedMinutes(sentAt);
        if (min >= 20) return "urgent";
        if (min >= 10) return "warning";
        return "normal";
    }
}

registry.category("actions").add("restaurant_suite.kds_backend", RestaurantKDSBackend);
export { RestaurantKDSBackend };
```

### 7.2 `static/src/js/kpi_dashboard.js`

```javascript
/** @odoo-module **/
// Copilot prompt:
// "Create an Odoo 19 Owl backend component RestaurantKPIDashboard.
//  Registered as 'restaurant_suite.kpi_dashboard'.
//  setup():
//    - state: dateFrom (first of month), dateTo (today), data null, loading, error
//    - onWillStart: call loadData()
//  loadData(): orm.call('restaurant.kpi', 'get_dashboard_data', [[], dateFrom, dateTo])
//  setPreset(preset): 'today'|'week'|'month' — update dates and reload
//  onDateChange(field, value): update state date field and reload
//  formatCurrency(value): Intl.NumberFormat fr-FR EUR
//  formatPct(value): value.toFixed(1) + '%'
//  Template: restaurant_suite.KPIDashboard
//  Cards: Revenue, Covers, Revenue/Cover, Food Cost %, Waste Value
//  Table: top_items with columns name/qty/revenue/margin
//  Charts: describe chart data but do NOT import Chart.js — leave chart rendering
//          as a comment for the Owl template to handle with a canvas ref"

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class RestaurantKPIDashboard extends Component {
    static template = "restaurant_suite.KPIDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            dateFrom: this._firstOfMonth(),
            dateTo: this._today(),
            data: null,
            loading: true,
            error: null,
        });
        onWillStart(async () => await this.loadData());
    }

    _today() { return new Date().toISOString().split("T")[0]; }
    _firstOfMonth() {
        const d = new Date();
        return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().split("T")[0];
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "restaurant.kpi", "get_dashboard_data",
                [[], this.state.dateFrom, this.state.dateTo]
            );
        } catch (e) {
            this.state.error = e.message || "Failed to load KPI data.";
        } finally {
            this.state.loading = false;
        }
    }

    async setPreset(preset) {
        const today = new Date();
        let from = new Date(today);
        if (preset === "week") from.setDate(today.getDate() - today.getDay());
        else if (preset === "month") from = new Date(today.getFullYear(), today.getMonth(), 1);
        this.state.dateFrom = from.toISOString().split("T")[0];
        this.state.dateTo = this._today();
        await this.loadData();
    }

    async onDateChange(field, ev) {
        this.state[field] = ev.target.value;
        await this.loadData();
    }

    formatCurrency(v) {
        return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(v || 0);
    }
    formatPct(v) { return `${(v || 0).toFixed(1)}%`; }
}

registry.category("actions").add("restaurant_suite.kpi_dashboard", RestaurantKPIDashboard);
export { RestaurantKPIDashboard };
```

---

## 8. Menus — `views/menus.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Top-level menu: Restaurant Suite -->
    <menuitem id="menu_restaurant_suite_root"
              name="Restaurant Suite"
              sequence="60"
              web_icon="restaurant_suite,static/description/icon.png"/>

    <!-- Configuration -->
    <menuitem id="menu_restaurant_config"
              name="Configuration"
              parent="menu_restaurant_suite_root"
              sequence="90"/>
    <menuitem id="menu_allergens"
              name="Allergens"
              parent="menu_restaurant_config"
              action="action_restaurant_allergen"
              sequence="10"/>
    <menuitem id="menu_scrap_reasons"
              name="Waste Reasons"
              parent="menu_restaurant_config"
              action="action_restaurant_scrap_reason"
              sequence="20"/>
    <menuitem id="menu_kds_stations"
              name="KDS Stations"
              parent="menu_restaurant_config"
              action="action_restaurant_kds_station"
              sequence="30"/>

    <!-- Operations -->
    <menuitem id="menu_restaurant_ops"
              name="Operations"
              parent="menu_restaurant_suite_root"
              sequence="10"/>
    <menuitem id="menu_recipes"
              name="Recipes"
              parent="menu_restaurant_ops"
              action="action_restaurant_recipe"
              sequence="10"/>
    <menuitem id="menu_par_levels"
              name="PAR Levels"
              parent="menu_restaurant_ops"
              action="action_restaurant_par_level"
              sequence="20"/>
    <menuitem id="menu_franchises"
              name="Franchises"
              parent="menu_restaurant_ops"
              action="action_restaurant_franchise"
              sequence="30"/>

    <!-- Reporting -->
    <menuitem id="menu_restaurant_reporting"
              name="Reporting"
              parent="menu_restaurant_suite_root"
              sequence="50"/>
    <menuitem id="menu_kpi_dashboard"
              name="KPI Dashboard"
              parent="menu_restaurant_reporting"
              action="action_restaurant_kpi_dashboard"
              sequence="10"/>
    <menuitem id="menu_kds_backend"
              name="Kitchen Display"
              parent="menu_restaurant_reporting"
              action="action_restaurant_kds_backend"
              sequence="20"/>
</odoo>
```

---

## 9. What NOT to Replicate — Reference Table

Use this table during code review. If Copilot suggests creating any of these, reject it.

| If Copilot tries to create... | Correct approach |
|---|---|
| `restaurant.floor` model | Use `pos.floor` — already in `point_of_sale` |
| `restaurant.table` model | Use `pos.table` — already in `point_of_sale` |
| `restaurant.course` model | Use native Course button in POS (no model needed) |
| `pos_order.fire_course()` | Already in Odoo 19 native POS JS |
| Split bill wizard for POS | Already native in Odoo 19 POS (Allow Bill Splitting setting) |
| `iface_table_management` on pos.config | Already exists natively — `_inherit` only if referencing |
| `pos.order.table_id` field | Already exists natively in Odoo 17+ |
| `pos.order.covers` field | Already exists natively in Odoo 17+ |
| `pos.order.line.note` field | Already exists natively |
| Preparation printer / kitchen printer | Already in native POS (Preparation Printers setting) |
| Duplicate `pos.floor` form view | Extend with `inherit_id` only |

---

## 10. `models/__init__.py`

```python
from . import restaurant_allergen
from . import restaurant_scrap_reason
from . import restaurant_recipe
from . import mrp_bom_line
from . import restaurant_kds_order       # includes RestaurantKdsStation
from . import par_level
from . import franchise
from . import restaurant_kpi
from . import pos_config                 # extend only
from . import pos_order                  # extend only — kds_state, create_kds_lines
from . import stock_scrap                # extend only — waste_reason_id
```

---

## 11. Demo Data — `demo/restaurant_demo.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Link to the NATIVE POS config, not a new one -->
        <!-- Assumes a pos.config already exists from base demo data -->

        <!-- Demo KDS Stations -->
        <record id="demo_station_hot" model="restaurant.kds.station">
            <field name="name">Chaud (Demo)</field>
            <field name="display_mode">ticket</field>
        </record>
        <record id="demo_station_cold" model="restaurant.kds.station">
            <field name="name">Froid / Entrées (Demo)</field>
            <field name="display_mode">ticket</field>
        </record>
        <record id="demo_station_bar" model="restaurant.kds.station">
            <field name="name">Bar (Demo)</field>
            <field name="display_mode">grid</field>
        </record>

        <!-- Demo PAR Level (if demo products exist) -->
        <!-- Add only if demo product exists to avoid install errors -->
    </data>
</odoo>
```

---

## 12. Key Copilot Prompting Patterns

### When extending a native model

```
@workspace Extend the native Odoo 19 model pos.order using _inherit.
DO NOT redefine existing fields (table_id, covers, lines, state).
Only add: [list new fields].
Check the Odoo 19 source for pos.order to confirm which fields already exist
before adding anything.
```

### When creating a new model that references native models

```
@workspace Create Odoo 19 model restaurant.kds.order.
It uses pos.table (native) for table_id — NOT a custom restaurant.table model.
It uses pos.order.line (native) for pos_order_line_id.
Never reference restaurant.floor or restaurant.table — those don't exist in this module.
```

### When adding to POS config

```
@workspace Extend pos.config with _inherit.
Only add fields that DO NOT already exist in Odoo 19 point_of_sale.
The following fields are ALREADY NATIVE and must not be redefined:
iface_table_management, floor_ids, is_table_management, allow_bill_splitting.
Only add: kds_station_ids (One2many restaurant.kds.station) and franchise_id.
```

---

## 13. Installation Checklist

```bash
# 1. Ensure point_of_sale, mrp, stock, purchase, account are already installed
# 2. Copy module to addons path
# 3. Install:
./odoo-bin -d your_db -i restaurant_suite --stop-after-init

# 4. After install, verify:
# - 14 EU allergens in Restaurant Suite > Configuration > Allergens
# - 6 waste reasons in Configuration > Waste Reasons
# - 2 cron jobs active (Settings > Scheduled Actions > search "Restaurant Suite")
# - KPI dashboard loads at Restaurant Suite > Reporting > KPI Dashboard
# - KDS screen loads at Restaurant Suite > Reporting > Kitchen Display

# 5. Enable native restaurant mode in POS:
# Point of Sale > Configuration > Settings > Is a Bar/Restaurant > ON
# Then configure floor plans natively at Point of Sale > Configuration > Floor Plans
```

---

*End of guide — `restaurant_suite` v19.0.1.0.0 — extend native, zero duplication*
