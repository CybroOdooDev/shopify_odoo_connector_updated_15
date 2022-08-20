# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (Contact : odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
#    USE OR OTHER DEALINGS IN THE SOFTWARE.
#
################################################################################

from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID
import dateutil.parser
import odoo
import pytz
import logging

_logger = logging.getLogger(__name__)


class WebHook(http.Controller):
    @http.route('/products', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_url(self, *args, **kwargs):
        print('for product webhook********************888')
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            if request.jsonrequest['options']:
                for option in request.jsonrequest['options']:
                    attribute_id = request.env['product.attribute'].with_user(
                        SUPERUSER_ID).search([
                        ('shopify_attribute_id', '=', option['id']),
                        ('shopify_instance_id', '=', shopify_instance_id.id)
                    ])
                    if attribute_id:
                        for opt_val in option['values']:
                            att_val_ids = attribute_id.value_ids.filtered(
                                lambda x: x.name == opt_val
                            )
                            if not att_val_ids:
                                att_val = {
                                    'name': opt_val
                                }
                                attribute_id.with_user(SUPERUSER_ID).write({
                                    'value_ids': [(0, 0, att_val)]
                                })
                    else:
                        attribute_id = request.env[
                            'product.attribute'].with_user(
                            SUPERUSER_ID).create({
                            'name': option['name'],
                            'shopify_attribute_id': option['id'],
                            'shopify_instance_id': shopify_instance_id.id
                        })
                        for opt_val in option['values']:
                            att_val = {
                                'name': opt_val,
                            }
                            attribute_id.with_user(SUPERUSER_ID).write({
                                'value_ids': [(0, 0, att_val)]
                            })
            product_id = request.env['product.template'].with_user(
                SUPERUSER_ID).create(
                {
                    "name": request.jsonrequest['title'],
                    "type": 'product',
                    "categ_id": request.env.ref(
                        'product.product_category_all').id,
                    "synced_product": True,
                    'description': request.jsonrequest['body_html'],
                    'shopify_product_id': request.jsonreqeuest['id'],
                    'shopify_instance_id': shopify_instance_id.id,
                    'company_id': shopify_instance_id.company_id.id,
                })
            if request.jsonrequest['options']:
                for option in request.jsonrequest['options']:
                    attribute_id = self.env[
                        'product.attribute'].with_user(SUPERUSER_ID).search(
                        [
                            ('shopify_attribute_id', '=', option['id']),
                            ('shopify_instance_id', '=', shopify_instance_id.id)
                        ])
                    # att_val_ids = attribute_id.value_ids
                    att_val_ids = self.env[
                        'product.attribute.value'].with_user(
                        SUPERUSER_ID).search([
                        ('name', 'in', option['values']),
                        ('attribute_id', '=', attribute_id.id)
                    ])
                    att_line = {
                        'attribute_id': attribute_id.id,
                        'value_ids': [(4, att_val.id) for att_val in
                                      att_val_ids]
                    }
                    product_id.with_user(SUPERUSER_ID).write({
                        'attribute_line_ids': [(0, 0, att_line)]
                    })
                for shopify_var in request.jsonrequest['variants']:
                    shopify_var_list = []
                    shopify_var_id_list = []
                    r = 3
                    for i in range(1, r):
                        if shopify_var['option' + str(i)] is not None:
                            shopify_var_list.append(
                                shopify_var['option' + str(i)])
                        else:
                            break
                    for option in request.jsonrequest['options']:
                        for var in shopify_var_list:
                            if var in option['values']:
                                attribute_id = self.env[
                                    'product.attribute'].sudo().search(
                                    [
                                        ('shopify_attribute_id', '=',
                                         option['id']),
                                        ('shopify_instance_id', '=',
                                         shopify_instance_id.id)
                                    ])
                                att_val_id = attribute_id.value_ids.filtered(
                                    lambda x: x.name == var
                                )
                                shopify_var_id_list.append(att_val_id)
                    for variant in product_id.product_variant_ids:
                        o_var_list = variant.product_template_variant_value_ids.mapped(
                            'product_attribute_value_id')
                        o_var_list = [rec for rec in o_var_list]
                        if o_var_list == shopify_var_id_list:
                            variant.sudo().write({
                                'shopify_variant_id': shopify_var['id'],
                                'shopify_instance_id': shopify_instance_id.id,
                                'synced_product': True,
                                'company_id': shopify_instance_id.company_id.id,
                                'default_code': shopify_var['sku'],
                            })
            else:
                for variant in product_id.product_variant_ids:
                    variant.sudo().write({
                        'shopify_variant_id': request.jsonrequest['id'],
                        'shopify_instance_id': shopify_instance_id.id,
                        'synced_product': True,
                        'company_id': shopify_instance_id.company_id.id,
                    })
            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}

    @http.route('/update_product', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_update_product_url(self, *args, **kwargs):
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            product_id = request.env['product.template'].with_user(
                SUPERUSER_ID).search([
                ('shopify_product_id', '=', request.jsonrequest['id']),
                ('shopify_instance_id', '=', shopify_instance_id.id),
                ('company_id', 'in', [False, shopify_instance_id.company_id.id])
            ])
            opt_list = []
            if product_id:
                product_id.with_user(SUPERUSER_ID).write({
                    'name': request.jsonrequest['title'],
                    'shopify_product_id': request.jsonrequest['id'],
                    'shopify_instance_id': shopify_instance_id.id,
                    'company_id': shopify_instance_id.company_id.id,
                    'description': request.jsonrequest['body_html'],
                })
                if request.jsonrequest['options'] and request.jsonrequest[
                    'variants']:
                    for shopify_var in request.jsonrequest['variants']:
                        variant_id = request.env['product.product'].with_user(
                            SUPERUSER_ID).search([
                            ('shopify_variant_id', '=', shopify_var['id']),
                            (
                                'shopify_instance_id', '=',
                                shopify_instance_id.id),
                            ('company_id', '=',
                             shopify_instance_id.company_id.id),
                        ])
                        if not variant_id:
                            for option in request.jsonrequest['options']:
                                attribute_id = request.env[
                                    'product.attribute'].with_user(
                                    SUPERUSER_ID).search([
                                    ('shopify_attribute_id', '=', option['id']),
                                    ('shopify_instance_id', '=',
                                     shopify_instance_id.id)
                                ])
                                if not attribute_id:
                                    attribute_id = request.env[
                                        'product.attribute'].with_user(
                                        SUPERUSER_ID).create({
                                        'name': option['name'],
                                        'shopify_attribute_id': option['id'],
                                        'shopify_instance_id':
                                            shopify_instance_id.id,
                                    })
                                    for opt_val in option['values']:
                                        att_val = {
                                            'name': opt_val
                                        }
                                        attribute_id.with_user(
                                            SUPERUSER_ID).write({
                                            'value_ids': [(0, 0, att_val)]
                                        })
                                    att_val_ids = request.env[
                                        'product.attribute.value'].with_user(
                                        SUPERUSER_ID).search([
                                        ('name', 'in', option['values']),
                                        ('attribute_id', '=', attribute_id.id)
                                    ])
                                    att_line = {
                                        'attribute_id': attribute_id.id,
                                        'value_ids': [(4, 0, 0, att_val_id.id)
                                                      for att_val_id in
                                                      att_val_ids]
                                    }
                                    product_id.with_user(SUPERUSER_ID).write({
                                        'attribute_line_ids': [(0, 0, att_line)]
                                    })
                            for shopify_variant in request.jsonrequest[
                                'variants']:
                                shopify_var_list = []
                                shopify_var_id_list = []
                                r = 4
                                for i in range(1, r):
                                    if shopify_variant[
                                        'option' + str(i)] is not None:
                                        shopify_var_list.append(
                                            shopify_variant['option' + str(i)])
                                    else:
                                        break
                                for option in request.jsonrequest['options']:
                                    for variant in shopify_var_list:
                                        if variant in option['values']:
                                            attribute_id = request.env[
                                                'product.attribute'].with_user(
                                                SUPERUSER_ID).search([
                                                ('shopify_attribute_id', '=',
                                                 option['id']),
                                                ('shopify_instance_id', '=',
                                                 shopify_instance_id.id)
                                            ])
                                            att_val_id = attribute_id.value_ids.filtered(
                                                lambda x: x.name == variant
                                            )
                                            shopify_var_id_list.append(
                                                att_val_id)
                                for odoo_var in product_id.product_variant_ids:
                                    odoo_var_list = odoo_var.product_template_variant_value_ids.mapped(
                                        'product_attribute_value_id')
                                    odoo_var_list = [rec for rec in
                                                     odoo_var_list]
                                    if odoo_var_list == shopify_var_id_list:
                                        odoo_var.with_user(SUPERUSER_ID).write({
                                            'shopify_variant_id':
                                                shopify_variant[
                                                    'id'],
                                            'shopify_instance_id': shopify_instance_id.id,
                                            'synced_product': True,
                                            'company_id': shopify_instance_id.company_id.id,
                                            'default_code': shopify_variant[
                                                'sku']
                                        })
                    for option in request.jsonrequest['options']:
                        opt_list.append(option['id'])
                    attributes = product_id.attribute_line_ids.mapped(
                        'attribute_id').mapped('shopify_attribute_id')
                    if len(product_id.attribute_line_ids) != len(
                            request.jsonrequest['options']):
                        for attribute in attributes:
                            if int(attribute) not in opt_list:
                                att_line_to_rm = product_id.attribute_line_ids.filtered(
                                    lambda
                                        x: x.attribute_id.shopify_attribute_id == attribute
                                )
                                att_line_to_rm.unlink()
            else:
                if request.jsonrequest['options']:
                    for option in request.jsonrequest['options']:
                        attribute_id = request.env[
                            'product.attribute'].with_user(
                            SUPERUSER_ID).search([
                            ('shopify_attribute_id', '=', option['id']),
                            ('shopify_instance_id', '=', shopify_instance_id.id)
                        ])
                        if attribute_id:
                            for opt_val in option['values']:
                                val = attribute_id.value_ids.filtered(
                                    lambda x: x.name == opt_val
                                )
                                if not val:
                                    att_val = {
                                        'name': opt_val
                                    }
                                    attribute_id.with_user(SUPERUSER_ID).write({
                                        'value_ids': [(0, 0, att_val)]
                                    })
                        else:
                            attribute_id = request.env[
                                'product.attribute'].with_user(
                                SUPERUSER_ID).create({
                                'name': option['name'],
                                'shopify_attribute_id': option['id'],
                                'shopify_instance_id': shopify_instance_id.id,
                            })
                            for opt_val in option['values']:
                                att_val = {
                                    'name': opt_val
                                }
                                attribute_id.with_user(SUPERUSER_ID).write({
                                    'value_ids': [(0, 0, att_val)]
                                })
                product_id = request.env['product.template'].with_user(
                    SUPERUSER_ID).create({
                    'name': request.jsonrequest['title'],
                    'type': 'product',
                    'categ_id': request.env.ref(
                        'product.product_category_all').id,
                    'synced_product': True,
                    'description': request.jsonrequest['body_html'],
                    'shopify_product_id': request.jsonrequest['id'],
                    'shopify_instance_id': shopify_instance_id.id,
                    'company_id': shopify_instance_id.company_id.id,
                })
                if request.jsonrequest['options']:
                    for option in request.jsonrequest['options']:
                        attribute_id = request.env[
                            'product.attribute'].with_user(
                            SUPERUSER_ID).search([
                            ('shopify_attribute_id', '=', option['id']),
                            ('shopify_instance_id', '=', shopify_instance_id.id)
                        ])
                        att_val_ids = request.env[
                            'product.attribute.value'].with_user(
                            SUPERUSER_ID).search([
                            ('name', 'in', option['values']),
                            ('attribute_id', '=', attribute_id.id)
                        ])
                        att_line = {
                            'attribute_id': attribute_id.id,
                            'value_ids': [(4, att_val.id) for att_val in
                                          att_val_ids]
                        }
                        product_id.with_user(SUPERUSER_ID).write({
                            'attribute_line_Ids': [(0, 0, att_line)]
                        })
                    for shopify_var in request.jsonrequest['variants']:
                        shopify_var_list = []
                        shopify_var_id_list = []
                        r = 4
                        for i in range(1, 4):
                            if shopify_var['options' + str(i)] is not None:
                                shopify_var_list.append(
                                    shopify_var['options' + str(i)])
                            else:
                                break
                        for option in request.jsonrequest['options']:
                            for variant in shopify_var_list:
                                if variant in option['values']:
                                    attribute_id = request.env[
                                        'product.attribute'].with_user(
                                        SUPERUSER_ID).search([
                                        ('shopify_attribute_id', '=',
                                         option['id']),
                                        ('shopify_instance_id', '=',
                                         shopify_instance_id.id)
                                    ])
                                    att_val_ids = attribute_id.with_user(
                                        SUPERUSER_ID).value_ids.filtered(
                                        lambda x: x.name == variant
                                    )
                        for odoo_var in product_id.product_variant_ids:
                            odoo_var_list = odoo_var.product_template_variant_value_ids.mapped(
                                'product_attribute_value_id')
                            odoo_var_list = [rec for rec in odoo_var_list]
                            if odoo_var_list == shopify_var_id_list:
                                odoo_var.with_user(SUPERUSER_ID).write({
                                    'shopify_variant_id': shopify_var['id'],
                                    'shopify_instance_id': shopify_instance_id.id,
                                    'synced_product': True,
                                    'company_id': shopify_instance_id.company_id.id,
                                    'default_code': shopify_var['sku']
                                })
                else:
                    for variant in product_id.product_variant_ids:
                        variant.with_user(SUPERUSER_ID).write({
                            'shopify_variant_id': request.jsonrequest['id'],
                            'shopify_instance_id': shopify_instance_id.id,
                            'synced_product': True,
                            'company_id': shopify_instance_id.company_id.id,
                        })
            return {'Messages': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/delete_product', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_delete_product_url(self, *args, **kwargs):
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            product_id = request.env['product.template'].with_user(
                SUPERUSER_ID).search([
                ('shopify_product_id', '=', request.jsonrequest['id']),
                ('shopify_instance_id', '=', shopify_instance_id.id),
                ('company_id', 'in', [False, shopify_instance_id.company_id.id])
            ], limit=1)
            if product_id:
                product_id.with_user(SUPERUSER_ID).write({
                    'active': False
                })
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/customers', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_customer_url(self, *args, **kwargs):
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            vals = {}
            if request.jsonrequest['addresses']:
                country_id = self.env['res.country'].sudo().search([
                    (
                        'name', '=',
                        request.jsonrequest['addresses'][0]['country'])
                ])
                state_id = self.env['res.country.state'].sudo().search([
                    ('name', '=',
                     request.jsonrequest['addresses'][0]['province'])
                ])
                vals = {
                    'street': request.jsonrequest['addresses'][0][
                        'address1'],
                    'street2': request.jsonrequest['addresses'][0][
                        'address2'],
                    'city': request.jsonrequest['addresses'][0]['city'],
                    'country_id': country_id.id if country_id else False,
                    'state_id': state_id.id if state_id else False,
                    'zip': request.jsonrequest['addresses'][0]['zip'],
                }
            if request.jsonrequest['first_name']:
                vals['name'] = request.jsonrequest['first_name']
            if request.jsonrequest['last_name']:
                if request.jsonrequest['first_name']:
                    vals['name'] = request.jsonrequest['first_name'] + ' ' + \
                                   request.jsonrequest['last_name']
                else:
                    vals['name'] = request.jsonrequest['last_name']
            if not request.jsonrequest['first_name'] and not \
                    request.jsonrequest[
                        'last_name'] and request.jsonrequest['email']:
                vals['name'] = request.jsonrequest['email']
            vals['email'] = request.jsonrequest['email']
            vals['phone'] = request.jsonrequest['phone']
            vals['shopify_customer_id'] = request.jsonrequest['id']
            vals['shopify_instance_id'] = shopify_instance_id.id
            vals['synced_customer'] = True
            vals['company_id'] = shopify_instance_id.company_id.id
            customer_id = request.env['res.partner'].with_user(
                SUPERUSER_ID).search([
                ('shopify_customer_id', '=', request.jsonrequest['id']),
                ('shopify_instance_id', '=', shopify_instance_id.id),
                ('company_id', 'in',
                 [False, shopify_instance_id.company_id.id])
            ], limit=1)
            if customer_id:
                customer_id.with_user(SUPERUSER_ID).write(vals)
            else:
                request.env['res.partner'].with_user(SUPERUSER_ID).create(vals)
            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}

    @http.route('/update_customer', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_update_customer_url(self, *args, **kwargs):
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            vals = {}
            if request.jsonrequest['addresses']:
                country_id = self.env['res.country'].sudo().search([
                    (
                        'name', '=',
                        request.jsonrequest['addresses'][0]['country'])
                ])
                state_id = self.env['res.country.state'].sudo().search([
                    ('name', '=',
                     request.jsonrequest['addresses'][0]['province'])
                ])
                vals = {
                    'street': request.jsonrequest['addresses'][0][
                        'address1'],
                    'street2': request.jsonrequest['addresses'][0][
                        'address2'],
                    'city': request.jsonrequest['addresses'][0]['city'],
                    'country_id': country_id.id if country_id else False,
                    'state_id': state_id.id if state_id else False,
                    'zip': request.jsonrequest['addresses'][0]['zip'],
                }
            if request.jsonrequest['first_name']:
                vals['name'] = request.jsonrequest['first_name']
            if request.jsonrequest['last_name']:
                if request.jsonrequest['first_name']:
                    vals['name'] = request.jsonrequest['first_name'] + ' ' + \
                                   request.jsonrequest['last_name']
                else:
                    vals['name'] = request.jsonrequest['last_name']
            if not request.jsonrequest['first_name'] and not \
                    request.jsonrequest[
                        'last_name'] and request.jsonrequest['email']:
                vals['name'] = request.jsonrequest['email']
            vals['email'] = request.jsonrequest['email']
            vals['phone'] = request.jsonrequest['phone']
            vals['shopify_customer_id'] = request.jsonrequest['id']
            vals['shopify_instance_id'] = shopify_instance_id.id
            vals['synced_customer'] = True
            vals['company_id'] = shopify_instance_id.company_id.id
            customer_id = request.env['res.partner'].with_user(
                SUPERUSER_ID).search([
                ('shopify_customer_id', '=', request.jsonrequest['id']),
                ('shopify_instance_id', '=', shopify_instance_id.id),
                ('company_id', 'in',
                 [False, shopify_instance_id.company_id.id])
            ], limit=1)
            if customer_id:
                customer_id.with_user(SUPERUSER_ID).write(vals)
            else:
                request.env['res.partner'].with_user(SUPERUSER_ID).create(vals)
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/delete_customer', type='json', auth='none', mehtods=['POST'],
                csrf=False)
    def get_webhook_delete_customer_url(self, *args, **kwargs):
        try:
            shop_name = request.httprequest.headers.get(
                'X-Shopify-Shop-Domain')
            shopify_instance_id = request.env[
                'shopify.configuration'].with_user(SUPERUSER_ID).search([
                ('shop_name', 'like', shop_name)
            ], limit=1)
            customer_id = request.env['res.partner'].with_user(
                SUPERUSER_ID).search([
                ('shopify_customer_id', '=', request.jsonrequest['id']),
                ('shopify_instance_id', '=', shopify_instance_id.id),
                ('company_id', 'in', [False, shopify_instance_id.company_id.id])
            ], limit=1)
            if customer_id:
                customer_id.with_user(SUPERUSER_ID).write({
                    'active': False,
                })
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/orders', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_order_url(self, *args, **kwargs):
        try:
            customer_name = request.jsonrequest['customer'].get(
                'first_name')
            partner_id = request.env['res.partner'].with_user(
                SUPERUSER_ID).search([('name', '=', customer_name)]).id
            if not partner_id:
                partner_id = request.env['res.partner'].with_user(
                    SUPERUSER_ID).create({'name': customer_name}).id
            so = request.env['sale.order'].with_user(SUPERUSER_ID).create({
                "partner_id": partner_id,
                "date_order": odoo.fields.Datetime.to_string(
                    dateutil.parser.parse(
                        request.jsonrequest['created_at']).astimezone(
                        pytz.utc)),
                "l10n_in_gst_treatment": "regular",
                "shopify_order_id": request.jsonrequest['id'],
                "synced_order": True,
                "name": request.jsonrequest['name']
            })
            if request.jsonrequest['tax_lines']:
                tax = request.jsonrequest['tax_lines'][0]['rate']
                tax_group = request.jsonrequest['tax_lines'][0]["title"]
                taxes = tax * 100
                tax_name = request.env[
                    'account.tax'].with_user(SUPERUSER_ID).search(
                    [('amount', '=', taxes),
                     ('tax_group_id', '=', tax_group),
                     ('type_tax_use', '=', 'sale')])
                if not tax_name:
                    tax_group_id = request.env[
                        'account.tax.group'].with_user(
                        SUPERUSER_ID).create({'name': tax_group})
                    tax_name = request.env['account.tax'].with_user(
                        SUPERUSER_ID).create(
                        {'name': tax_group + str(taxes) + '%',
                         'type_tax_use': 'sale',
                         'amount_type': 'percent',
                         'tax_group_id': tax_group_id.id,
                         'amount': taxes,
                         })
            else:
                tax_name = None
            if request.jsonrequest['line_items']:
                line_items = request.jsonrequest['line_items']
                for line in line_items:
                    product_name = line['title']
                    product_id = request.env['product.product'].with_user(
                        SUPERUSER_ID).search(
                        [('name', '=', product_name)]).id
                    if not product_id:
                        product_id = request.env[
                            'product.product'].with_user(
                            SUPERUSER_ID).create(
                            {'name': product_name}).id
                    line_values = {
                        "product_id": product_id,
                        "price_unit": line['price'],
                        "product_uom_qty": line['quantity'],
                        'order_id': so.id,
                        'tax_id': tax_name,
                    }
                    request.env['sale.order.line'].with_user(
                        SUPERUSER_ID).create(line_values)
            return {"Message": "Success"}
        except Exception as e:
            return {"Message": "Something went wrong"}

    @http.route('/update_order', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_update_order_url(self, *args, **kwargs):
        try:
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/cancel_order', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_cancel_order_url(self, *args, **kwargs):
        try:
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/order_fulfillment', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_order_fulfillment_url(self, *args, **kwargs):
        try:
            if request.jsonrequest['id']:
                shop_name = request.httprequest.headers.get(
                    'X-Shopify-Shop-Domain')
                shopify_instance_id = request.env[
                    'shopify.configuration'].with_user(SUPERUSER_ID).search([
                    ('shop_name', 'like', shop_name)
                ], limit=1)
                fulfillment_status = request.jsonrequest['fulfillment_status']
                order_id = request.env['sale.order'].with_user(
                    SUPERUSER_ID).sarch([
                    ('shopify_order_id', '=', request.jsonrequest['id']),
                    ('shopify_instance_id', '=', shopify_instance_id.id),
                    ('company_id', 'in',
                     [False, shopify_instance_id.company_id.id])
                ])
                if order_id:
                    order_id.with_user(SUPERUSER_ID).write({
                        'fulfillment_status': 'fulfilled'
                        if fulfillment_status == 'fulfilled'
                        else 'partially_fulfilled'
                        if fulfillment_status == 'partially_fulfilled'
                        else 'unfulfilled'
                    })
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}

    @http.route('/order_payment', type='json', auth='none', methods=['POST'],
                csrf=False)
    def get_webhook_order_payment_url(self, *args, **kwargs):
        try:
            if request.jsonrequest['id']:
                shop_name = request.httprequest.headers.get(
                    'X-Shopify-Shop-Domain')
                shopify_instance_id = request.env[
                    'shopify.configuration'].with_user(SUPERUSER_ID).search([
                    ('shop_name', 'like', shop_name)
                ], limit=1)
                payment_status = request.jsonrequest['financial_status']
                order_id = request.env['sale.order'].with_user(
                    SUPERUSER_ID).sarch([
                    ('shopify_order_id', '=', request.jsonrequest['id']),
                    ('shopify_instance_id', '=', shopify_instance_id.id),
                    ('company_id', 'in',
                     [False, shopify_instance_id.company_id.id])
                ])
                if order_id:
                    order_id.with_user(SUPERUSER_ID).write({
                        'payment_status': 'paid' if payment_status == 'paid'
                        else 'partially_paid'
                        if payment_status == 'partially_paid'
                        else 'partially_refunded'
                        if payment_status == 'partially_refunded'
                        else 'refunded' if payment_status == 'refunded'
                        else 'unpaid',
                    })
                else:
                    request.env['shopify.payment'].with_user(
                        SUPERUSER_ID).create({
                        'shopify_order_id': request.jsonrequest['id'],
                        'payment_status': 'paid' if payment_status == 'paid'
                        else 'partially_paid'
                        if payment_status == 'partially_paid'
                        else 'partially_refunded'
                        if payment_status == 'partially_refunded'
                        else 'refunded' if payment_status == 'refunded'
                        else 'unpaid',
                        'company_id': shopify_instance_id.company_id.id,
                        'shopify_instance_id': shopify_instance_id.id,
                    })
            return {'Message': 'Success'}
        except Exception as e:
            return {'Message': 'Something went Wrong'}
