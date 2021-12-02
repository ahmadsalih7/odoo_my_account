# -*- coding: utf-8 -*-
from odoo import models, fields, api , _

class MyaccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancels an account move by reversing it.
    """
    _name = 'myaccount.move.reversal'
    _description = 'Account Move Reversal'
    move_id = fields.Many2one('myaccount.move', string='Journal Entry',
                              domain=[('state', '=', 'posted')])
    date = fields.Date(string='Reversal date', default=fields.Date.context_today, required=True)
    # company_currency_id = fields.Many2one(related='move_id.company_currency_id', string='Company Currency',
    #                                       readonly=True,
    #                                       store=True)


    def reverse_moves(self):
        pass