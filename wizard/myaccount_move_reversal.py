# -*- coding: utf-8 -*-
from odoo import models, fields, _


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
        move = self.env['myaccount.move'].browse(self.env.context['active_ids'])
        default_values_list = {
            'ref': _(f'Reversal of {move.name}'),
            'date': move.date,
            'state': 'posted'
        }
        move_id = self.env['myaccount.move'].create(default_values_list)

        print(default_values_list)
        for record in move.line_ids:
            line = {
                'move_id': move_id.id,
                'account_id': record.account_id.id,
                'credit': record.debit,
                'debit': record.credit,
                'balance': record.balance,
            }
            self.env['myaccount.move.line'].create(line)