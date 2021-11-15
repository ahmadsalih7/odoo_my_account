#-*- coding: utf-8 -*-

from odoo import models, fields, api


class my_account(models.Model):
    _name = 'myaccount.myaccount'
    _description = 'Chart of accounts '

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    reconcile = fields.Boolean(string='Allow Reconciliation')
    deprecate = fields.Boolean(string='Deprecated')

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
