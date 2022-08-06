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
import ast
import random
import logging
import requests
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from babel.dates import format_date
from odoo.exceptions import ValidationError
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)


class ShopifyConnector(models.Model):
    _name = 'shopify.configuration'
    _description = 'Shopify Connector'
    _rec_name = 'name'

    def _compute_kanban_dashboard(self):
        for shopify_instance in self:
            shopify_instance.kanban_dashboard = json.dumps(
                shopify_instance.get_shopify_configuration_details())

    def _compute_kanban_dashboard_graph(self):
        for shopify_instance in self:
            # if shopify_instance.state == 'new':
            #     shopify_instance.kanban_dashboard_graph = False
            # else:
            shopify_instance.kanban_dashboard_graph = json.dumps(
                shopify_instance.get_graph())

    name = fields.Char(string='Instance Name', required=True)
    con_endpoint = fields.Char(string='API', required=True)
    consumer_key = fields.Char(string='Password', required=True)
    consumer_secret = fields.Char(string='Secret', required=True)
    shop_name = fields.Char(string='Store Name', required=True)
    version = fields.Char(string='Version', required=True)
    last_synced = fields.Datetime(string='Last Synced')
    state = fields.Selection([('new', 'Not Connected'),
                              ('sync', 'Connected'), ],
                             'Status', readonly=True, index=True, default='new')
    import_product = fields.Boolean(string='Import Products')
    import_customer = fields.Boolean(string='Import Customer')
    import_order = fields.Boolean(string='Import Orders')
    webhook_product = fields.Char(string='Product Url')
    webhook_customer = fields.Char(string='Customer Url')
    webhook_order = fields.Char(string='Order Url')
    webhook_payment = fields.Char('Payment Url')
    webhook_fulfillment = fields.Char('Fulfillment Url')
    webhook_product_update = fields.Char('Product Update Url')
    webhook_product_delete = fields.Char('Product Delete Url')
    webhook_customer_update = fields.Char('Customer Update Url')
    webhook_customer_delete = fields.Char('Customer Delete Url')
    webhook_order_update = fields.Char('Order Update Url')
    webhook_order_delete = fields.Char('Order Delete Url')
    company_id = fields.Many2one('res.company', 'Company', required=True)
    customer_ids = fields.One2many('res.partner', 'shopify_instance_id',
                                   string='Customers')
    product_ids = fields.One2many('product.template', 'shopify_instance_id',
                                  string='Products', store=True)
    order_ids = fields.One2many('sale.order', 'shopify_instance_id',
                                string='Orders', store=True)
    customer_count = fields.Integer('Customers', compute='_compute_counts')
    product_count = fields.Integer('Products', compute='_compute_counts')
    order_count = fields.Integer('Orders', compute='_compute_counts')
    kanban_dashboard = fields.Text(compute='_compute_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(
        compute='_compute_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean('Show on Dashboard', default=True)
    color = fields.Integer('Color', default=0)

    def _compute_counts(self):
        for shopify in self:
            # customer_count = self.env['res.partner'].search_count([
            #     ('shopify_instance_id', '=', shopify.id),
            #     ('shopify_customer_id', '!=', False),
            #     ('company_id', '=', shopify.company_id.id)
            # ])
            # product_count = self.env['product.template'].search_count([
            #     ('shopify_instance_id', '=', shopify.id),
            #     ('shopify_product_id', '!=', False),
            #     ('company_id', '=', shopify.company_id.id)
            # ])
            # order_count = self.env['sale.order'].search_count([
            #     ('shopify_instance_id', '=', shopify.id),
            #     ('shopify_order_id', '!=', False),
            #     ('company_id', '=', shopify.company_id.id)
            # ])
            shopify.customer_count = len(shopify.customer_ids)
            shopify.product_count = len(shopify.product_ids)
            shopify.order_count = len(shopify.order_ids)

    def shopify_customers(self):
        self.ensure_one()
        if len(self.customer_ids) == 1:
            form = self.env.ref('base.view_partner_form', False)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.customer_ids.id,
                'view_mode': 'form',
                'view_id': form.id,
                'views': [(form.id, 'form')],
            }
        elif len(self.customer_ids) > 1:
            return {
                'name': 'Shopify Customers',
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.customer_ids.ids)]
            }
        else:
            return {
                'type': 'ir.actions.act_window_close'
            }

    def shopify_products(self):
        self.ensure_one()
        if len(self.product_ids) == 1:
            form = self.env.ref('product.product_template_only_form_view',
                                False)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'res_id': self.product_ids.id,
                'view_mode': 'form',
                'view_id': form.id,
                'views': [(form.id, 'form')],
            }
        elif len(self.product_ids) > 1:
            return {
                'name': 'Shopify Customers',
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.product_ids.ids)]
            }
        else:
            return {
                'type': 'ir.actions.act_window_close'
            }

    def shopify_orders(self):
        self.ensure_one()
        if len(self.order_ids) == 1:
            form = self.env.ref('sale.view_order_form', False)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.order_ids.id,
                'view_mode': 'form',
                'view_id': form.id,
                'views': [(form.id, 'form')],
            }
        elif len(self.order_ids) > 1:
            return {
                'name': 'Shopify Customers',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.order_ids.ids)]
            }
        else:
            return {
                'type': 'ir.actions.act_window_close'
            }

    def sync_shopify(self):
        api_key = self.con_endpoint
        PASSWORD = self.consumer_key
        # PASSWORD = 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
        # PASSWORD for devloper account = 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
        store_name = self.shop_name
        version = self.version
        url = "https://%s:%s@%s/admin/api/%s/storefront_access_tokens.json" % (
            api_key, PASSWORD, store_name, version)
        payload = json.dumps({
            "storefront_access_token": {
                "title": "Test"
            }
        })
        headers = {
            'Content-Type': 'application/json'

        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            self.state = "sync"
        else:
            raise ValidationError(
                _("Invalid Credentials provided .Please check them "))

    def sync_shopify_all(self):
        api_key = self.con_endpoint
        PASSWORD = self.consumer_key
        store_name = self.shop_name
        version = self.version
        if self.import_product:
            product_url = "https://%s:%s@%s/admin/api/%s/products.json" % (
                api_key, PASSWORD, store_name, version)
            self.ensure_one()
            if self.last_synced:
                product = self.env['product.template'].search(
                    [('create_date', '>=', self.last_synced)])
            else:
                product = self.env['product.template'].search([])
            for rec in product:
                if not rec.synced_product:
                    rec.synced_product = True
                    variants = []
                    for line in rec.attribute_line_ids.value_ids:
                        line_vals = {
                            "option1": line.name,
                        }
                        variants.append(line_vals)
                    product_attribute = self.env['product.attribute']
                    options = []

                    for line in rec.attribute_line_ids:
                        vals = {
                            "name": line.attribute_id.name,
                        }
                        options.append(vals)
                    payload = json.dumps({
                        "product": {
                            "title": rec.name,
                            "body_html": "",
                            "product_type": rec.type,
                            "variants": variants,
                            "options": options,

                        }
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.request("POST", product_url,
                                                headers=headers,
                                                data=payload)
        if self.import_customer:
            customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
                api_key, PASSWORD, store_name, version)
            if self.last_synced:
                partner = self.env['res.partner'].search(
                    [('create_date', '>=', self.last_synced)])
            else:
                partner = self.env['res.partner'].search([])
            for customer in partner:
                if not customer.synced_customer:
                    customer.synced_customer = True
                    payload = json.dumps({
                        "customer": {
                            "first_name": customer.name,
                            "last_name": "",
                            "email": customer.email,
                            "phone": customer.phone,
                            "verified_email": True,
                            "addresses": [
                                {
                                    "address1": customer.street,
                                    "city": customer.city,
                                    "province": "",
                                    "phone": customer.phone,
                                    "zip": customer.zip,
                                    "last_name": "",
                                    "first_name": customer.name,
                                    "country": customer.country_id.name
                                }
                            ],
                            "send_email_invite": True
                        }
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.request("POST", customer_url,
                                                headers=headers,
                                                data=payload)
        if self.import_order:
            order_url = "https://%s:%s@%s/admin/api/%s/draft_orders.json" % (
                api_key, PASSWORD, store_name, version)
            if self.last_synced:
                sale_order = self.env['sale.order'].search(
                    [('create_date', '>=', self.last_synced),
                     ('state', '=', 'draft')])
            else:
                sale_order = self.env['sale.order'].search(
                    [('state', '=', 'draft')])
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
        self.last_synced = datetime.datetime.now()

    def open_shopify_instance(self):
        print('open action')
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'shopify_odoo_connector.action_shopify_configuration')
        print('action', action)
        context = self._context.copy()
        if 'context' in action and type(action['context']) == str:
            context.update(ast.literal_eval(action['context']))
        else:
            context.update(action.get('context', {}))
        action['context'] = context
        # action['context'].update({
        #     'default_id': self.id,
        #     'search_default_id': self.id,
        # })
        action['domain'] = [('id', '=', self.id)]
        # action['view_mode'] = 'form'
        # action['views'] = [(False, 'form')]
        # action['context'] = dict(self._context, create=False)
        print('last action', action)
        return action

    def get_shopify_configuration_details(self):
        print('get_shopify_configuration_details')
        customer_count = self.customer_count
        product_count = self.product_count
        sale_count = self.order_count
        sale_income_this_month = 0.0
        sale_income_this_year = 0.0
        sale_income_last_month = 0.0
        return {
            'customer_count': customer_count,
            'product_count': product_count,
            'sale_count': sale_count,
            'sale_income_this_year': sale_income_this_year,
            'sale_income_this_month': sale_income_this_month,
            'sale_income_last_month': sale_income_last_month,
            'company_count': len(self.env.companies),
        }

    def get_graph(self):
        print('get graph')
        def graph_data(date, amount):
            nm = format_date(date, 'd LLLL Y', locale=locale)
            short_nm = format_date(date, 'd MMM', locale=locale)
            return {'x': short_nm, 'y': amount, 'name': nm}

        data = []
        locale = get_lang(self.env).code
        today = datetime.today()
        for i in range(30, 0, -5):
            current_date = today + timedelta(days=-i)
            data.append(graph_data(current_date, random.randint(-5, 15)))
        print('data', data)
        return [
            {'values': data, 'title': '', 'key': 'Sale Income', 'area': True,
             'color': '#7c7bad', 'is_sample_data': False}]


class ShopifyPayment(models.Model):
    _name = 'shopify.payment'
    _description = 'Shopify Payments'

    shopify_order_id = fields.Char('Shopify Order Id', readonly=True,
                                   store=True)
    payment_status = fields.Selection([('paid', 'Paid'), ('unpaid', 'Unpaid'),
                                       ('partially_paid', 'Partially Paid'),
                                       ('refunded', 'Refunded'), (
                                           'partially_refunded',
                                           'Partially Refunded')],
                                      string='Payment Status')
    company_id = fields.Many2one('res.company', 'Company')
    shopify_instance_id = fields.Many2one('shopify.configuration',
                                          'Shopify Instance')
