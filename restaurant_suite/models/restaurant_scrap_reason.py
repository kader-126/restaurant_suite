from odoo import fields, models


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
