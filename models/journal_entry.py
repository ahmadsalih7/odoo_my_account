# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class my_accountMoveLine(models.Model):
    _name = "myaccount.move.line"
    _description = "Journal item"

    account_id = fields.Many2one('myaccount.myaccount', required=True)
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
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True,
                                     currency_field='company_currency_id')

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(my_accountMoveLine, self).default_get(default_fields)
        if 'account_id' in default_fields \
                and not values.get('account_id') \
                and self._context.get('default_type') == 'out_invoice':
            # Fill missing 'account_id'.
            journal = self.env['myaccount.journal'].browse(
                self._context.get('default_journal_id'))
            values['account_id'] = journal.default_credit_account_id.id
        return values

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

    @api.model
    def _get_price_total_and_subtotal(self):
        price_unit = self.price_unit
        quantity = self.quantity
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

    def _get_default_journal(self):
        move_type = self._context.get('default_type')
        journal_type = 'general'
        if move_type == 'entry':
            journal_type = 'general'
        if move_type == 'out_invoice':
            journal_type = 'sale'
        domain = [('company_id', '=', self.env.user.company_id.id), ('type', '=', journal_type)]
        journal = self.env['myaccount.journal'].search(domain, limit=1)
        return journal

    type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
    ], string='Type', required=True, store=True, readonly=True, tracking=True,
        default="entry", change_default=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    name = fields.Char(string='Number', required=True, copy=False, readonly=True, default='/')
    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    ref = fields.Char(string='Move Ref', copy=False)
    line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Journal Items')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    journal_id = fields.Many2one('myaccount.journal', string='Journal', required=True, readonly=True, store=True,
                                 states={'draft': [('readonly', False)]}, default=_get_default_journal)

    # =========================================================
    # Invoice related fields
    # =========================================================

    invoice_date = fields.Date(string='Invoice/Bill Date', copy=False)
    invoice_line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Invoice lines',
                                       copy=False)

    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment', store=True, readonly=True, copy=False, tracking=True,
        default='not_paid')

    # =========================================================
    # Amount fields fields
    # =========================================================
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                                   compute='_compute_amount',
                                   currency_field='company_currency_id')

    def action_post(self):
        if self.name == '/':
            # if it's a new record
            if self.type == 'entry':
                name = self.env['ir.sequence'].next_by_code('myaccount.move') or '/'
            elif self.type == 'out_invoice':
                name = self.env['ir.sequence'].next_by_code('myaccount.move.invoices') or '/'
        else:
            name = self.name
        self.write({'state': 'posted',
                    'name': name})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_invoice_register_payment(self):
        return self.env['myaccount.payment'] \
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id) \
            .action_register_payment()
        # self.write({'invoice_payment_state': 'in_payment'})

    def _get_move_display_name(self):
        draft_name = ''
        if self.state == 'draft':
            draft_name += {
                'out_invoice': _('Draft Invoice'),
                'entry': _('Draft Entry')
            }[self.type]
            draft_name += ' (* %s)' % str(self.id)
        return draft_name

    def name_get(self):
        result = []
        for move in self:
            if move.state == 'draft':
                name = move._get_move_display_name()
                result.append((move.id, name))
            else:
                result.append((move.id, move.name))
        return result

    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_amount(self):
        for move in self:
            move.amount_total = 0.0
            total = 0
            for line in move.invoice_line_ids:
                total += line.price_subtotal
            move.amount_total = total
