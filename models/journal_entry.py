# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class my_accountMoveLine(models.Model):
    _name = "myaccount.move.line"
    _description = "Journal item"

    account_id = fields.Many2one('myaccount.myaccount', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    name = fields.Char(string='label')
    exclude_from_invoice_tab = fields.Boolean()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False)
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    move_id = fields.Many2one('myaccount.move')
    balance = fields.Monetary(string='Balance', default=0.0, store=True,
                              currency_field='company_currency_id',
                              compute='_compute_balance')
    product_id = fields.Many2one('my_product.template', string="Product")
    payment_id = fields.Many2one('myaccount.payment', string="Originator Payment", copy=False)
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
        elif 'account_id' in default_fields \
                and not values.get('account_id') \
                and self._context.get('default_type') == 'in_invoice':
            # Fill missing 'account_id'.
            journal = self.env['myaccount.journal'].browse(
                self._context.get('default_journal_id'))
            values['account_id'] = journal.default_debit_account_id.id
        elif self._context.get('line_ids') and any(
                field_name in default_fields for field_name in ('debit', 'credit')):
            move = self.env['myaccount.move'].new({'line_ids': self._context['line_ids']})
            # Suggest default value for debit / credit to balance the journal entry.
            balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
            if balance < 0.0:
                values.update({'debit': -balance})
            if balance > 0.0:
                values.update({'credit': balance})

        return values

    # -----------------------------
    # Helpers
    # -----------------------------

    @api.model
    def _get_price_total_and_subtotal(self):
        price_unit = self.price_unit
        quantity = self.quantity
        discount = self.discount

        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        return {'price_subtotal': subtotal}

    @api.model
    def create(self, vals):
        return super(my_accountMoveLine, self).create(vals)

    # -----------------------------
    # On change methods
    # -----------------------------

    @api.onchange('debit')
    def on_change_debit(self):
        if self.debit:
            self.credit = 0.0

    @api.onchange('credit')
    def on_change_credit(self):
        if self.credit:
            self.debit = 0.0

    @api.onchange('product_id')
    def on_change_product_id(self):
        self.price_unit = self.product_id.list_price
        self.name = self.product_id.name

    @api.onchange('quantity', 'discount', 'price_unit')
    def _onchange_price_subtotal(self):
        for line in self:
            line.update(line._get_price_total_and_subtotal())

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit


class my_accountMove(models.Model):
    _name = "myaccount.move"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Journal Entries"

    def _get_default_journal(self):
        move_type = self._context.get('default_type')
        journal_type = 'general'
        if move_type == 'entry':
            journal_type = 'general'
        elif move_type == 'out_invoice':
            journal_type = 'sale'
        elif move_type == 'in_invoice':
            journal_type = 'purchase'
        domain = [('company_id', '=', self.env.user.company_id.id), ('type', '=', journal_type)]
        journal = self.env['myaccount.journal'].search(domain, limit=1)
        return journal

    type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bills'),
    ], string='Type', required=True, store=True, readonly=True, tracking=True,
        default="entry", change_default=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    name = fields.Char(string='Number', required=True, copy=False, readonly=True, default='/')
    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    ref = fields.Char(string='Move Ref', copy=False)
    line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Journal Items', copy=True)
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
                                       domain=[('exclude_from_invoice_tab', '=', False)],
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
        if not self.partner_id:
            raise UserError(
                _("The field 'Customer' is required, please complete it to validate the Customer Invoice."))

        if self.name == '/':
            # if it's a new record
            if self.journal_id.type == 'general':
                name = self.env['ir.sequence'].next_by_code('myaccount.move') or '/'
            elif self.journal_id.type == 'sale':
                name = self.env['ir.sequence'].next_by_code('myaccount.move.invoices') or '/'
            elif self.journal_id.type == 'cash':
                name = self.env['ir.sequence'].next_by_code('myaccount.payment.cash') or '/'
            elif self.journal_id.type == 'bank':
                name = self.env['ir.sequence'].next_by_code('myaccount.payment.bank') or '/'
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

    def _recompute_journal_lines(self):
        def _get_main_account(self, existing_term_lines):
            if existing_term_lines:
                # Retrieve account from previous lines in order to allow the user to set a custom one.
                return existing_term_lines[0].account_id
            else:
                # Search new account.
                domain = [
                    ('internal_type', '=', 'receivable'),
                ]
                return self.env['myaccount.myaccount'].search(domain, limit=1)

        def _update_journal_lines(self, journal_line, amount):
            for line in journal_line:
                line.update({
                    'credit': line.price_subtotal
                })

        def _update_main_account(self, terms_line, amount, account_id):
            new_terms_lines = self.env['myaccount.move.line']
            if terms_line:
                # There is a receivable account then just update the amount
                receivable_line = terms_line[0]  # In this case it must be only one line
                receivable_line.update({
                    'debit': amount
                })
            else:
                # There is no receivable line then create new
                receivable_line = self.env['myaccount.move.line'].create({
                    'move_id': self.id,
                    'account_id': account_id.id,
                    'debit': amount,
                    'exclude_from_invoice_tab': True,
                })
            new_terms_lines += receivable_line
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')
        other_journal_lines = self.line_ids.filtered(lambda line: line.account_id.internal_type != 'receivable')
        subtotal_sum = sum(other_journal_lines.mapped('price_subtotal'))
        if not other_journal_lines:
            self.line_ids -= existing_terms_lines
            return

        account_id = _get_main_account(self, existing_terms_lines)
        new_terms_lines = _update_main_account(self, existing_terms_lines, subtotal_sum, account_id)
        _update_journal_lines(self, other_journal_lines, subtotal_sum)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

    # -----------------------------
    # On change methods
    # -----------------------------

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        self.line_ids = self.line_ids.filtered(lambda line: line.exclude_from_invoice_tab) + self.invoice_line_ids
        self._recompute_journal_lines()
        self.invoice_line_ids = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    @api.model
    def create(self, vals):
        def filter_line(line):
            invoices = vals.get('invoice_line_ids', 0)
            if not invoices:
                return True
            if line[0] != 0:
                return True
            if invoices and line[1] not in [invoice[1] for invoice in invoices]:
                return True
            return False

        vals['line_ids'] = list(filter(filter_line, vals['line_ids']))
        return super(my_accountMove, self).create(vals)
