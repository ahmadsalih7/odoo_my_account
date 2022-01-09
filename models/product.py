# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _name = "my_product.template"
    _description = "Product Template"
    _order = "name"

    name = fields.Char('Name', required=True)
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