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
        - EU-14 allergen master linked to recipes
        - Waste reason tracking on stock.scrap

        Does NOT recreate: floors, tables, courses, split bill, preparation printers.
        Those are used as-is from the native point_of_sale module.
    """,
    'author': 'Restaurant Suite Team',
    'depends': [
        'point_of_sale',
        'mrp',
        'stock',
        'purchase',
        'account',
        'mail',
        'web',
    ],
    'data': [
        'security/restaurant_security.xml',
        'security/ir.model.access.csv',
        'data/restaurant_data.xml',
        'data/cron_data.xml',
        'views/restaurant_allergen_views.xml',
        'views/restaurant_recipe_views.xml',
        'views/restaurant_kds_views.xml',
        'views/par_level_views.xml',
        'wizard/royalty_invoice_wizard_views.xml',
        'views/franchise_views.xml',
        'views/kpi_dashboard_views.xml',
        'views/menus.xml',
        'views/pos_config_views_extend.xml',
        'views/stock_scrap_views_extend.xml',
        'report/food_cost_report.xml',
        'report/recipe_card_report.xml',
        'wizard/royalty_invoice_wizard_views.xml',
    ],
    'assets': {
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
