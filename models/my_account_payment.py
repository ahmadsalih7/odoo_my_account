# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class account_payment(models.Model):
    _name = "myaccount.payment"
    _description = "Payments"

    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        active_id = self._context.get('active_id')
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_id or active_model != 'account.move':
            return rec

        invoice = self.env['myaccount.move'].browse(active_id)
        rec.update({
            'communication': invoice.name,
            'amount': invoice.amount_total,
            'partner_id': invoice.partner_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',

        })
        invoices = self.env['myaccount.move'].browse(active_ids)

        # Check all invoices are open
        if any(invoice.state != 'posted' or invoice.invoice_payment_state != 'not_paid' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        if 'invoice_ids' not in rec:
            rec['invoice_ids'] = [(6, 0, invoices.ids)]
        return rec

    name = fields.Char(readonly=True, copy=False)
    communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Monetary(string='Amount', required=True, readonly=True, states={'draft': [('readonly', False)]},
                             tracking=True, currency_field='company_currency_id')
    payment_date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
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
    destination_account_id = fields.Many2one('myaccount.myaccount', compute='_compute_destination_account_id', readonly=True)
    invoice_ids = fields.Many2many('myaccount.move', 'myaccount_invoice_payment_rel', 'payment_id', 'invoice_id',
                                   string="Invoices", copy=False, readonly=True)

    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for payment in self:
            if payment.invoice_ids:
                payment.destination_account_id = payment.invoice_ids[0].mapped(
                    'line_ids.account_id').filtered(
                    lambda account: account.internal_type in ('receivable', 'payable'))[0].id

    def action_register_payment(self):
        return {
            'name': _('Register Payment'),
            'res_model': 'myaccount.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('my_account.view_account_payment_invoice_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _prepare_payment_moves(self):
        all_move_vals = []
        for payment in self:
            # name used for receivable line
            rec_pay_line_name = 'Customer Payment'
            if payment.invoice_ids:
                rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))
                # name used for in liquidity line
            liquidity_line_name = payment.name
            move_vals = {
                'date': payment.payment_date,
                'ref': payment.communication,
                'journal_id': payment.journal_id.id,
                'partner_id': payment.partner_id.id,
                'line_ids': [
                    # Receivable line.
                    (0, 0, {
                        'name': rec_pay_line_name,
                        'debit': 0.0,
                        'credit': payment.amount,
                        'partner_id': payment.partner_id.id,
                        'account_id': payment.destination_account_id.id,
                        'payment_id': payment.id
                    }),
                    # Liquidity line.
                    (0, 0, {
                        'name': liquidity_line_name,
                        'debit': payment.amount,
                        'credit': 0.0,
                        'partner_id': payment.partner_id.id,
                        'account_id': payment.journal_id.default_debit_account_id.id,
                        'payment_id': payment.id
                    }),
                ]
            }
            all_move_vals.append(move_vals)
        return all_move_vals

    def post(self):
        account_move = self.env['myaccount.move'].with_context(default_type='entry')
        for rec in self:
            sequence_code = "account.payment.customer.invoice"
            if not rec.name:
                rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
            moves = account_move.create(rec._prepare_payment_moves())
            moves.action_post()
