# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class account_payment(models.Model):
    _name = "myaccount.payment"
    _description = "Payments"

    name = fields.Char(readonly=True, copy=False)
    communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    payment_type = fields.Selection(
        [('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')],
        string='Payment Type', required=True, readonly=True, states={'draft': [('readonly', False)]})

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], tracking=True, readonly=True,
                                    states={'draft': [('readonly', False)]})
    state = fields.Selection(
        [('draft', 'Draft'), ('posted', 'Validated'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),
         ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    journal_id = fields.Many2one('myaccount.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, tracking=True,
                                 domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")

    def action_register_payment(self):
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_account_payment_invoice_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
