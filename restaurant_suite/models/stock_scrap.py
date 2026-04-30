from odoo import fields, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    waste_reason_id = fields.Many2one(
        'restaurant.scrap.reason',
        string='Waste Reason',
        help='Restaurant Suite: categorizes the reason for this scrap.',
    )
