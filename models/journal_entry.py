#-*- coding: utf-8 -*-

from odoo import models, fields, api


class my_accountMoveLine(models.Model):
    _name = "myaccount.move.line"
    _description = "Journal item"

    account_id = fields.Many2one('myaccount.myaccount')
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    name = fields.Char(string='label')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True, store=True)    
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    move_id = fields.Many2one('myaccount.move')
    balance = fields.Monetary(string='Balance', default=0.0, currency_field='company_currency_id')

    ####################
    # Helper Functions
    ####################
    @api.model
    def get_balance(self):
        return self.move_id.line_ids[0].balance

    ####################
    # On change methods
    ####################

    @api.onchange('debit')
    def onChangeDebit(self):
        old_balance = self.get_balance()
        if old_balance == 0.0 and self.debit != 0.0:
            self.balance = -1 * self.debit
        elif old_balance > 0.0 and self.debit == 0.0:
            self.debit = old_balance

    @api.onchange('credit')
    def onChangeCredit(self):
        old_balance = self.get_balance()
        if old_balance == 0.0 and self.credit != 0.0:
            self.balance = self.credit
        elif old_balance < 0.0 and self.credit == 0.0:
            self.credit = -1 * old_balance

class my_accountMove(models.Model):
    _name = "myaccount.move"
    _description = "Journal Entries"

    date = fields.Date(string='Date', required=True, index=True, readonly=True, default=fields.Date.context_today)
    ref = fields.Char(string='Reference', copy=False)
    line_ids = fields.One2many('myaccount.move.line', 'move_id',string='Journal Items')

