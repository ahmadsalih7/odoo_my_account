#-*- coding: utf-8 -*-

from odoo import models, fields, api


class my_account(models.Model):
    _name = 'myaccount.myaccount'
    _description = 'Chart of accounts '
    _order = 'code'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    tag_ids = fields.Many2many('myaccount.myaccount.tag', 'name', string='Tags')
    reconcile = fields.Boolean(string='Allow Reconciliation')
    deprecate = fields.Boolean(string='Deprecated')

    def name_get(self):
        """ Show code beside account name """
        result = []
        for rec in self:
            result.append((rec.id, f'{rec.code}   {rec.name}'))
        return result


class my_accountAcountTag(models.Model):
    _name = 'myaccount.myaccount.tag'
    _description = 'tags of accounts '

    name = fields.Char(string='Name', required=True)
    

class MyAccountJournal(models.Model):
    _name = "myaccount.journal"
    _description = "Journal"

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Short Code', size=5, required=True,
                       help="The journal entries of this journal will be named using this prefix.")
    sequence = fields.Integer(default=10)
    sequence_number_next = fields.Integer(string='Next Number', compute='_compute_seq_number_next')

    active = fields.Boolean(default=True, help="Set active to false to hide the Journal without removing it.")
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'Miscellaneous'),
    ], required=True)

    sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence',
                                  required=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True,
                                          store=True)
    default_credit_account_id = fields.Many2one('myaccount.myaccount', string='Default Credit Account',
                                                domain=[('deprecated', '=', False)],
                                                help="It acts as a default account for credit amount",
                                                ondelete='restrict')
    default_debit_account_id = fields.Many2one('myaccount.myaccount', string='Default Debit Account',
                                               domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                               help="It acts as a default account for debit amount",
                                               ondelete='restrict')

    def name_get(self):
        """ Show currency beside journal name """
        result = []
        for rec in self:
            result.append((rec.id, f'{rec.name} ({rec.company_currency_id.name})'))
        return result

    def _compute_seq_number_next(self):
        '''Compute 'sequence_number_next' according to the current sequence in use,
        an ir.sequence or an ir.sequence.date_range.
        '''
        for journal in self:
            if journal.sequence_id:
                sequence = journal.sequence_id._get_current_sequence()
                journal.sequence_number_next = sequence.number_next_actual
            else:
                journal.sequence_number_next = 1