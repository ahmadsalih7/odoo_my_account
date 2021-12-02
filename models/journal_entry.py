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
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    move_id = fields.Many2one('myaccount.move')
    balance = fields.Monetary(string='Balance', default=0.0, currency_field='company_currency_id')

    def total_balance(self):
        total = 0
        for line in self.move_id.line_ids:
            total += line.balance
        return total


    def recompute_fields(self):
        if not self.debit and not self.credit and not self.balance:
            current_balance = self.total_balance()
            if current_balance > 0.0 :
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



    ####################
    # On change methods
    ####################

    @api.onchange('debit')
    def onChangeDebit(self):
        if self.debit:
            self.credit = 0.0
        self.recompute_fields()

    @api.onchange('credit')
    def onChangeCredit(self):
        if self.credit:
            self.debit = 0.0
        self.recompute_fields()





class my_accountMove(models.Model):
    _name = "myaccount.move"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Journal Entries"

    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    ref = fields.Char(string='Move Ref', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    line_ids = fields.One2many('myaccount.move.line', 'move_id', string='Journal Items')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')


    def action_post(self):
        self.write({'state': 'posted'})

    def action_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def create(self,vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('myaccount.move') or _('New')
        return super(my_accountMove, self).create(vals)
