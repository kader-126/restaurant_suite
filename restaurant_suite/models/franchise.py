import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RestaurantFranchise(models.Model):
    _name = 'restaurant.franchise'
    _description = 'Franchise Royalty Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, string='Franchise Branch Company')
    hq_company_id = fields.Many2one('res.company', required=True, string='HQ Company')
    hq_partner_id = fields.Many2one('res.partner', related='hq_company_id.partner_id', readonly=True)
    royalty_rate = fields.Float(default=5.0, digits=(5, 2), tracking=True)
    royalty_base = fields.Selection(
        [
            ('revenue', 'Gross Revenue (POS Sales)'),
            ('profit', 'Net Profit'),
        ],
        default='revenue',
        required=True,
    )
    royalty_account_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        domain=[('account_type', 'in', ('expense', 'expense_direct_cost'))],
    )
    royalty_journal_id = fields.Many2one(
        'account.journal',
        company_dependent=True,
        domain=[('type', 'in', ('purchase', 'general'))],
    )

    def _get_period_revenue(self, date_from, date_to):
        self.ensure_one()
        self.env.cr.execute(
            """
            SELECT COALESCE(SUM(amount_total), 0)
            FROM pos_order
            WHERE state IN ('paid', 'done', 'invoiced')
              AND company_id = %s
              AND date_order::date >= %s
              AND date_order::date < %s
            """,
            (self.company_id.id, date_from, date_to),
        )
        return float(self.env.cr.fetchone()[0] or 0)

    def compute_monthly_royalty(self, date_from, date_to):
        self.ensure_one()
        revenue = self._get_period_revenue(date_from, date_to)
        amount = revenue * self.royalty_rate / 100.0
        if amount <= 0:
            _logger.info('Franchise %s: no revenue %s-%s', self.name, date_from, date_to)
            return False

        if not self.royalty_account_id or not self.royalty_journal_id:
            _logger.warning('Franchise %s missing royalty account/journal configuration.', self.name)
            return False

        invoice = self.env['account.move'].with_company(self.company_id).create(
            {
                'move_type': 'in_invoice',
                'partner_id': self.hq_partner_id.id,
                'company_id': self.company_id.id,
                'journal_id': self.royalty_journal_id.id,
                'invoice_date': date_to,
                'ref': f'Royalty {date_from} -> {date_to}',
                'invoice_line_ids': [
                    (
                        0,
                        0,
                        {
                            'name': f'Royalty {self.royalty_rate}% on {self.royalty_base} ({date_from} -> {date_to})',
                            'account_id': self.royalty_account_id.id,
                            'quantity': 1.0,
                            'price_unit': amount,
                        },
                    )
                ],
            }
        )
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
            except Exception as exc:  # pragma: no cover
                _logger.exception('Royalty error for %s: %s', franchise.name, exc)
