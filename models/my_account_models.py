#-*- coding: utf-8 -*-

from odoo import models, fields, api


class my_account(models.Model):
    _name = 'myaccount.myaccount'
    _description = 'Chart of accounts '

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    tag_ids = fields.Many2many('myaccount.myaccount.tag', 'name', string='Tags')
    reconcile = fields.Boolean(string='Allow Reconciliation')
    deprecate = fields.Boolean(string='Deprecated')


class my_accountAcountTag(models.Model):
    _name = 'myaccount.myaccount.tag'
    _description = 'tags of accounts '

    name = fields.Char(string='Name', required=True)
    

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
