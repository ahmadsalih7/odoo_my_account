# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _name = "my_product.template"
    _description = "Product Template"
    _order = "name"

    def _default_currency_id(self):
        company_id = self.env.context.get('force_company') or self.env.context.get('company_id') or self.env.company.id
        return self.env['res.company'].browse(company_id).currency_id

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company.id)
    sale_ok = fields.Boolean('Can be Sold', default=True)
    purchase_ok = fields.Boolean('Can be Purchased', default=True)
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service')], string='Product Type', default='consu', required=True)
    default_code = fields.Char('Internal Reference')
    barcode = fields.Char(string='Barcode')
    list_price = fields.Float('Sales Price', default=1.0)
    description = fields.Text('Description')

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, f'[{rec.barcode}] - {rec.name}'))
        return result