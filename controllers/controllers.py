# -*- coding: utf-8 -*-
# from odoo import http


# class MyAccount(http.Controller):
#     @http.route('/my_account/my_account/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/my_account/my_account/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('my_account.listing', {
#             'root': '/my_account/my_account',
#             'objects': http.request.env['my_account.my_account'].search([]),
#         })

#     @http.route('/my_account/my_account/objects/<model("my_account.my_account"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('my_account.object', {
#             'object': obj
#         })
