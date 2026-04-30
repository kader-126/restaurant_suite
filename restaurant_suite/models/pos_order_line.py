from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    kds_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('preparing', 'In Preparation'),
            ('ready', 'Ready'),
            ('served', 'Served'),
        ],
        default='pending',
        string='KDS Status',
        copy=False,
    )
    kds_sent = fields.Boolean(default=False, copy=False)
