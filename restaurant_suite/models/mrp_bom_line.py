from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    yield_ratio = fields.Float(
        string='Yield Ratio',
        default=1.0,
        digits=(5, 4),
        help='1kg raw -> 0.80kg usable = 0.80. Used in restaurant_suite food cost.',
    )
    waste_reason = fields.Char(
        string='Waste Reason',
        help='e.g. peeling, trimming, cooking loss',
    )

    @api.constrains('yield_ratio')
    def _check_yield_ratio(self):
        for line in self:
            if not (0.01 <= line.yield_ratio <= 1.0):
                raise ValidationError(
                    f'Yield ratio for "{line.product_id.display_name}" must be between 0.01 and 1.0.'
                )
