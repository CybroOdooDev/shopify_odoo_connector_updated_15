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

from odoo import models, fields, api, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_instance_id = fields.Many2one('shopify.configuration',
                                          string="Shopify Instance")
    synced_order = fields.Boolean(readonly=True, store=True)
    shopify_order_id = fields.Char(string="Shopify Id", readonly=True,
                                   store=True)
    shopify_order_name = fields.Char('Shopify Order', readonly=True, store=True)
    shopify_order_number = fields.Char('Shopify Order Bo', readonly=True,
                                       store=True)
    payment_status = fields.Selection([('paid', 'Paid'),
                                       ('partially_paid', 'Partially Paid'),
                                       ('unpaid', 'Unpaid'),
                                       ('refunded', 'Refunded'),
                                       ('partially_refunded',
                                        'Partially Refunded')],
                                      string='Shopify Payment Status',
                                      default='unpaid', readonly=True,
                                      store=True)
    fulfillment_status = fields.Selection([('fulfilled', 'Fulfilled'),
                                           ('partially_fulfilled',
                                            'Partially Fulfiled'),
                                           ('un_fulfilled', 'Un Fulfilled')],
                                          string='Fulfillment Status',
                                          default='un_fulfilled',
                                          readonly=True, store=True)

    def sync_shopify_order(self):
        print("Hello")
        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version
        customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
            api_key, PASSWORD, store_name, version)
        payload = {}
        headers = {
            'Content-Type': 'application/json'
        }
        response_customer = requests.request("GET", customer_url,
                                             headers=headers, data=payload)
        order_url = "https://%s:%s@%s/admin/api/%s/draft_orders.json" % (
            api_key, PASSWORD, store_name, version)
        order = self.env['sale.order'].search([('id', '=', self.id)])
        if not self.synced_order:
            print("1")
            self.synced_order = True
            line_items = []
            first_name = order.partner_id.name
            for line in self.order_line:
                line_vals = {
                    "title": line.product_id.name,
                    "price": line.price_unit,
                    "quantity": int(line.product_uom_qty),

                }
                line_items.append(line_vals)
            payload = json.dumps({
                "draft_order": {
                    "line_items": line_items,
                    "email": self.partner_id.email,
                    "use_customer_default_address": True
                }
            })
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.request("POST", order_url, headers=headers,
                                        data=payload)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version
        customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
            api_key, PASSWORD, store_name, version)
        payload = {}
        headers = {
            'Content-Type': 'application/json'
        }
        if self.shopify_order_id and self.shopify_instance_id:
            order_complete_url = "https://%s:%s@%s/admin/api/%s/draft_orders/%s/complete.json" % (
                api_key, PASSWORD, store_name, version, self.shopify_order_id)

            order = self.env['sale.order'].search([('id', '=', self.id)])
            line_items = []
            first_name = order.partner_id.name
            for line in self.order_line:
                line_vals = {
                    "title": line.product_id.name,
                    "price": line.price_unit,
                    "quantity": int(line.product_uom_qty),

                }
                line_items.append(line_vals)
            payload = json.dumps({
                "draft_order": {
                    "line_items": line_items,
                    "email": self.partner_id.email,
                    "id": self.shopify_order_id,
                    "status": "completed",
                    "use_customer_default_address": True
                }
            })
            response = requests.request("PUT", order_complete_url,
                                        headers=headers,
                                        data=payload)

        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_refund_line = fields.Boolean('Is Refund Line', default=False,
                                    readonly=True)
    shopify_line_id = fields.Char('Shopify Line Id', readonly=True, store=True)
    shopify_instance_id = fields.Char('Shopify Instance Id', readonly=True)
    shopify_taxable = fields.Boolean('Line Item Taxable', default=False)
    shopify_tax_amount = fields.Float('Shopify Tax Amount')
    shopify_discount_amount = fields.Float('Shopify Discount Amount')
    shopify_line_item_discount = fields.Float('Line Item Discount')
    shopify_discount_code = fields.Char('Shopify Discount Code')
