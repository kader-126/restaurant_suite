from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    kds_station_ids = fields.One2many(
        'restaurant.kds.station',
        'pos_config_id',
        string='KDS Stations (Restaurant Suite)',
    )
    franchise_id = fields.Many2one(
        'restaurant.franchise',
        string='Franchise Config',
        help='Link this POS to a franchise for royalty computation.',
    )
