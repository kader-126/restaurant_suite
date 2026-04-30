from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class RoyaltyInvoiceWizard(models.TransientModel):
    _name = 'restaurant.royalty.invoice.wizard'
    _description = 'Generate Franchise Royalty Invoice'

    franchise_id = fields.Many2one('restaurant.franchise', required=True)
    date_from = fields.Date(required=True, default=lambda self: date.today().replace(day=1) - relativedelta(months=1))
    date_to = fields.Date(required=True, default=lambda self: date.today().replace(day=1))

    def action_generate_invoice(self):
        self.ensure_one()
        invoice = self.franchise_id.compute_monthly_royalty(self.date_from, self.date_to)
        if not invoice:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
