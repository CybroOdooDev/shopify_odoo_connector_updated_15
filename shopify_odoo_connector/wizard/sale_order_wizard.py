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
from odoo import models, fields, _
import requests
import json
import dateutil.parser
import odoo
import pytz
from odoo.exceptions import ValidationError


class OrderWizard(models.TransientModel):
    _name = 'order.wizard'
    _description = 'Order Wizard'

    import_orders = fields.Selection(string='Import/Export',
                                     selection=[('shopify', 'To Shopify'),
                                                ('odoo', 'From Shopify')],
                                     required=True, default='odoo')
    shopify_instance_id = fields.Many2one('shopify.configuration',
                                          string="Shopify Instance",
                                          required=True)


    def sync_orders(self):
        shopify_instance = self.shopify_instance_id
        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version

        if self.import_orders == 'shopify':
            order_url = "https://%s:%s@%s/admin/api/%s/draft_orders.json" % (
                api_key, PASSWORD, store_name, version)
            sale_order = self.env['sale.order'].search(
                [('state', '=', 'draft'),
                 ('company_id', 'in', [False,
                                       shopify_instance.company_id.id])])
            for order in sale_order:
                if not order.synced_order:
                    order.synced_order = True
                    line_items = []
                    for line in order.order_line:
                        line_vals = {
                            "title": line.product_id.name,
                            "price": line.price_unit,
                            "quantity": int(line.product_uom_qty),

                        }
                        line_items.append(line_vals)
                    payload = json.dumps({
                        "draft_order": {
                            "line_items": line_items,
                            "email": order.partner_id.email,
                            "use_customer_default_address": True
                        }
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.request("POST", order_url,
                                                headers=headers,
                                                data=payload)
        else:
            order_url = "https://%s:%s@%s/admin/api/%s/orders.json" % (
                api_key, PASSWORD, store_name, version)
            payload = []
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("GET", order_url,
                                        headers=headers,
                                        data=payload)
            j = response.json()
            vals = {}
            for each in j['orders']:
                shopify_id = each['id']
                existing_order = self.env['sale.order'].search(
                    [('shopify_order_id', '=', shopify_id)])
                if not existing_order:
                    if each['customer']:
                        customer_id = each['customer'].get('id')
                        customer_name = each['customer'].get(
                            'first_name') + ' ' + each['customer'].get(
                            'last_name')
                        partner_id = self.env['res.partner'].sudo().search(
                            [('shopify_customer_id', '=', customer_id),
                             ('shopify_instance_id', '=',
                              shopify_instance.id),
                             ('company_id', 'in',
                              [shopify_instance.company_id.id, False])],
                            limit=1).id
                        if not partner_id:
                            partner_id = self.env[
                                'res.partner'].sudo().create(
                                {
                                    'name': customer_name,
                                    'shopify_customer_id': customer_id,
                                    'shopify_instance_id': shopify_instance.id,
                                    'company_id': shopify_instance.company_id.id
                                }).id
                        # customer_name = each['customer']['first_name']
                        # partner_id = self.env['res.partner'].search(
                        #     [('name', '=', customer_name)]).id
                        vals["partner_id"] = partner_id
                        # if not partner_id:
                        #     partner_id = self.env['res.partner'].create(
                        #         {'name': customer_name}).id
                        #     vals["partner_id"] = partner_id
                    else:
                        # raise ValidationError(
                        #     _("There is no customer set for one or more orders."))
                        continue
                    if each['tax_lines']:
                        tax = each['tax_lines'][0]['rate']
                        tax_group = each['tax_lines'][0]["title"]
                        taxes = tax * 100
                        tax_name = self.env[
                            'account.tax'].search(
                            [('amount', '=', taxes),
                             ('tax_group_id', '=', tax_group),
                             ('type_tax_use', '=', 'sale')])

                        if not tax_name:
                            tax_group_id = self.env['account.tax.group'].create(
                                {'name': tax_group})
                            tax_name = self.env['account.tax'].create(
                                {'name': tax_group + str(taxes) + '%',
                                 'type_tax_use': 'sale',
                                 'amount_type': 'percent',
                                 'tax_group_id': tax_group_id.id,
                                 'amount': taxes,
                                 })
                    else:
                        tax_name = None
                    vals["date_order"] = str(odoo.fields.Datetime.to_string(
                        dateutil.parser.parse(each['created_at']).astimezone(
                            pytz.utc)))
                    vals["l10n_in_gst_treatment"] = "regular"
                    vals["shopify_order_id"] = each['id']
                    vals["synced_order"] = True
                    vals["name"] = each['name']
                    sale_order = self.env['sale.order']
                    so = sale_order.create(vals)
                    currency = self.env['res.currency'].sudo().search(
                        [
                            ('name', 'ilike', each['currency']),
                            ('active', 'in', [False, True]),
                        ])
                    if currency and not currency.active:
                        currency.sudo().write({
                            'active': True,
                        })
                    line_vals_list = []
                    for line in each['line_items']:
                        discount = 0.0
                        if line['discount_allocations']:
                            discount = line['discount_allocations'][0]['amount']
                        product_shopify_id = line['variant_id'] if line[
                            'variant_id'] else line['product_id']
                        product_name = line['title']
                        product_id = self.env[
                            'product.product'].sudo().search(
                            [
                                ('shopify_variant_id', '=', product_shopify_id),
                                ('shopify_instance_id', '=', shopify_instance.id),
                                ('company_id', 'in',
                                 [shopify_instance.company_id.id, False])
                            ]).id
                        if not product_id:
                            product_id = self.env[
                                'product.product'].sudo().create(
                                {
                                    'name': product_name,
                                    'shopify_variant_id': product_shopify_id,
                                    'shopify_instance_id': shopify_instance.id,
                                    'company_id': shopify_instance.company_id.id,
                                    'synced_product': True,
                                })
                        str_list = []
                        for desc_index in line['discount_allocations']:
                            discount_type = \
                                each['discount_applications'][
                                    desc_index['discount_application_index']][
                                    'type']
                            if discount_type == 'discount_code':
                                str_list.append(
                                    each[
                                        'discount_applications'][
                                        desc_index[
                                            'discount_application_index']][
                                        'code'])
                            else:
                                str_list.append(
                                    each[
                                        'discount_applications'][
                                        desc_index[
                                            'discount_application_index']][
                                        'title'])
                        line_vals = {
                            'product_id': product_id,
                            'price_unit': line['price'],
                            'quantity': line['quantity'],
                            'currency_id': currency.id,
                            'discount': (float(discount) / float(
                                line['price']) * 100) / float(line['quantity'])
                            if discount else 0,
                            'tax_ids': [
                                (6, 0, tax_name.ids)] if tax_name else False,
                            'shopify_line_id': line['id'],
                            'shopify_instance_id': shopify_instance.id,
                            'shopify_taxable': line['taxable'],
                            'shopify_tax_amount': float(
                                line['tax_lines'][0]['price']) if
                            line['tax_lines'] else 0.0,
                            'shopify_discount_amount':
                                sum(float(i['amount']) for
                                    i in line['discount_allocations']) if line[
                                    'discount_allocations'] else 0.0,
                            'shopify_line_item_discount':
                                sum(float(
                                    each[
                                        'discount_applications'][
                                        i['discount_application_index']][
                                        'value']) for i in
                                    line['discount_allocations']) if
                                each[
                                    'discount_applications'] else 0.0,
                            'shopify_discount_code': ','.join(str_list),
                            'order_id': so.id,
                            'company_id': shopify_instance.company_id.id,
                        }
                        line_vals_list.append(line_vals)
                    if each['shipping_lines']:
                        shipping_lines = each['shipping_lines']
                        product_id = self.env.ref(
                            'shopify_plus.product_shopify_shipping')
                        for line in shipping_lines:
                            line_vals = {
                                'product_id': product_id.id,
                                'name': line['title'] if line[
                                    'title'] else product_id.name,
                                'price_unit': line['price'],
                                'quantity': 1,
                                'shopify_line_id': line['id'],
                                'order_id': so.id,
                                'shopify_instance_id': shopify_instance.id,
                                'company_id': shopify_instance.company_id.id,
                            }
                            line_vals_list.append(line_vals)
                    sale_order_line = self.env['sale.order.line']
                    sale_order_line.create(line_vals_list)
                    # for line in each['line_items']:
                    #     product_name = line['title']
                    #     product_id = self.env['product.product'].search(
                    #         [('name', '=', product_name)]).id
                    #     if not product_id:
                    #         product_id = self.env['product.product'].create(
                    #             {'name': product_name}).id
                    #
                    #     line_values = {
                    #         "product_id": product_id,
                    #         "price_unit": line['price'],
                    #         "product_uom_qty": line['quantity'],
                    #         'order_id': so.id,
                    #         'tax_id': tax_name,
                    #     }

