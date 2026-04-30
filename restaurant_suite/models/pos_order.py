from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    kds_state = fields.Selection(
        [
            ('idle', 'No items sent to KDS'),
            ('partial', 'Some items in kitchen'),
            ('all_sent', 'All items sent'),
            ('ready', 'All items ready'),
            ('served', 'Fully served'),
        ],
        compute='_compute_kds_state',
        store=True,
        string='KDS State',
    )

    @api.depends('lines', 'lines.kds_sent', 'lines.kds_status')
    def _compute_kds_state(self):
        kds_model = self.env['restaurant.kds.order']
        for order in self:
            kds_lines = kds_model.search([('pos_order_id', '=', order.id)])
            if not kds_lines:
                order.kds_state = 'idle'
                continue

            all_lines = order.lines
            if len(kds_lines) < len(all_lines):
                order.kds_state = 'partial'
            elif all(line.kitchen_status == 'served' for line in kds_lines):
                order.kds_state = 'served'
            elif all(line.kitchen_status in ('ready', 'served') for line in kds_lines):
                order.kds_state = 'ready'
            else:
                order.kds_state = 'all_sent'

    def create_kds_lines(self, station_id):
        self.ensure_one()
        station = self.env['restaurant.kds.station'].browse(station_id).exists()
        if not station:
            return False

        kds_model = self.env['restaurant.kds.order']
        existing_line_ids = set(
            kds_model.search([('pos_order_id', '=', self.id)]).mapped('pos_order_line_id').ids
        )

        for line in self.lines:
            if line.id in existing_line_ids:
                continue

            if station.pos_category_ids:
                product = line.product_id
                category_ids = set()
                if 'pos_categ_id' in product._fields and product.pos_categ_id:
                    category_ids.add(product.pos_categ_id.id)
                if 'pos_categ_ids' in product._fields:
                    category_ids.update(product.pos_categ_ids.ids)

                if category_ids.isdisjoint(set(station.pos_category_ids.ids)):
                    continue

            kds_model.create(
                {
                    'pos_order_line_id': line.id,
                    'station_id': station.id,
                    'sent_at': fields.Datetime.now(),
                    'kitchen_status': 'pending',
                }
            )
            line.write({'kds_sent': True, 'kds_status': 'pending'})

        return True
