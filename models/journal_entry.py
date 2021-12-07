# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class my_accountMoveLine(models.Model):
    _name = "myaccount.move.line"
    _description = "Journal item"

    account_id = fields.Many2one('myaccount.myaccount')
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    name = fields.Char(string='label')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False)
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    move_id = fields.Many2one('myaccount.move')
    balance = fields.Monetary(string='Balance', default=0.0, currency_field='company_currency_id')

    product_id = fields.Many2one('my_product.template', string="Product")
    quantity  =  fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True,
                                     currency_field='company_currency_id')

    # -----------------------------
    # Helpers
    # -----------------------------

    def recompute_fields(self):
        if not self.debit and not self.credit and not self.balance:
            current_balance = sum(line.balance for line in self.move_id.line_ids)
            if current_balance > 0.0:
                self.debit = current_balance
            else:
                self.credit = -1 * current_balance
            self.balance = 0
            return
        if self.debit:
            self.balance = -1 * self.debit
            return
        else:
            self.balance = self.credit

    def _get_price_total_and_subtotal(self):
        price_unit = self.price_unit
        quantity =self.quantity
        discount = self.discount

        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        return {'price_subtotal': subtotal}

    # -----------------------------
    # On change methods
    # -----------------------------

    @api.onchange('debit')
    def on_change_debit(self):
        if self.debit:
            self.credit = 0.0
        self.recompute_fields()

    @api.onchange('credit')
    def on_change_credit(self):
        if self.credit:
            self.debit = 0.0
        self.recompute_fields()

    @api.onchange('product_id')
    def on_change_product_id(self):
        self.price_unit = self.product_id.list_price

    @api.onchange('quantity', 'discount', 'price_unit')
    def _onchange_price_subtotal(self):
        for line in self:
            line.update(line._get_price_total_and_subtotal())

class my_accountMove(models.Model):
    _name = "myaccount.move"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Journal Entries"

    type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
    ], string='Type', required=True, store=True, readonly=True, tracking=True,
        default="entry", change_default=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    name = fields.Char(string='Number', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    ref = fields.Char(string='Move Ref', copy=False)
    line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Journal Items')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    # =========================================================
    # Invoice related fields
    # =========================================================

    invoice_date = fields.Date(string='Invoice/Bill Date', copy=False)
    invoice_line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Invoice lines',
                                       copy=False)

    def action_post(self):
        self.write({'state': 'posted'})

    def action_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('myaccount.move') or _('New')
        return super(my_accountMove, self).create(vals)
