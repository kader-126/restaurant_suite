from odoo import fields, models


class RestaurantAllergen(models.Model):
    _name = 'restaurant.allergen'
    _description = 'Food Allergen - EU Regulation 1169/2011'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(size=5)
    description = fields.Text(translate=True)
    icon = fields.Binary()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Allergen code must be unique.'),
    ]
