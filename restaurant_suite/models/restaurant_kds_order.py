from odoo import api, fields, models


class RestaurantKdsOrder(models.Model):
    _name = 'restaurant.kds.order'
    _description = 'KDS Backend Order Line Tracking'
    _order = 'sent_at asc, id asc'

    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        required=True,
        ondelete='cascade',
        index=True,
    )
    pos_order_id = fields.Many2one('pos.order', related='pos_order_line_id.order_id', store=True)
    table_id = fields.Many2one('pos.table', string='Table', store=True, compute='_compute_table')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', store=True)
    qty = fields.Float(related='pos_order_line_id.qty', store=True)
    note = fields.Char(related='pos_order_line_id.note', store=True)
    covers = fields.Integer(related='pos_order_id.covers', store=True)
    station_id = fields.Many2one('restaurant.kds.station', string='Kitchen Station', index=True)
    sent_at = fields.Datetime(default=fields.Datetime.now)
    kitchen_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('preparing', 'In Preparation'),
            ('ready', 'Ready'),
            ('served', 'Served'),
        ],
        default='pending',
        index=True,
    )

    def action_mark_preparing(self):
        self.write({'kitchen_status': 'preparing'})
        self.mapped('pos_order_line_id').write({'kds_status': 'preparing', 'kds_sent': True})

    def action_mark_ready(self):
        self.write({'kitchen_status': 'ready'})
        self.mapped('pos_order_line_id').write({'kds_status': 'ready', 'kds_sent': True})
        for rec in self:
            rec._notify_pos_if_order_complete(rec.pos_order_id)

    def action_mark_served(self):
        self.write({'kitchen_status': 'served'})
        self.mapped('pos_order_line_id').write({'kds_status': 'served', 'kds_sent': True})

    def _notify_pos_if_order_complete(self, order):
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

    @api.depends('pos_order_id')
    def _compute_table(self):
        for rec in self:
            tbl = False
            if rec.pos_order_id:
                tbl = getattr(rec.pos_order_id, 'table_id', False)
            rec.table_id = tbl

    @api.model
    def get_pending_for_station(self, station_id):
        lines = self.search(
            [
                ('station_id', '=', station_id),
                ('kitchen_status', 'in', ['pending', 'preparing']),
            ],
            order='sent_at asc, id asc',
        )

        orders = {}
        for line in lines:
            oid = line.pos_order_id.id
            if oid not in orders:
                orders[oid] = {
                    'order_id': oid,
                    'order_name': line.pos_order_id.name,
                    'table_name': line.table_id.name if line.table_id else 'Takeaway',
                    'covers': line.covers,
                    'sent_at': fields.Datetime.to_string(line.sent_at) if line.sent_at else None,
                    'lines': [],
                }
            orders[oid]['lines'].append(
                {
                    'kds_id': line.id,
                    'product_name': line.product_id.display_name,
                    'qty': line.qty,
                    'note': line.note or '',
                    'kitchen_status': line.kitchen_status,
                }
            )
        return list(orders.values())


class RestaurantKdsStation(models.Model):
    _name = 'restaurant.kds.station'
    _description = 'Backend KDS Station'
    _order = 'name'

    name = fields.Char(required=True)
    pos_config_id = fields.Many2one('pos.config', ondelete='cascade', index=True)
    pos_category_ids = fields.Many2many(
        'pos.category',
        string='POS Product Categories',
        help='Orders with products in these categories are routed to this station.',
    )
    display_mode = fields.Selection(
        [
            ('ticket', 'Ticket View'),
            ('grid', 'Grid View'),
        ],
        default='ticket',
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
