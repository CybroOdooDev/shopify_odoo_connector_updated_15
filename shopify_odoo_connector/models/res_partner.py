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


class Partners(models.Model):
    _inherit = 'res.partner'

    shopify_instance_id = fields.Many2one('shopify.configuration',
                                  string="Shopify Instance")
    synced_customer = fields.Boolean(readonly=True, store=True)
    shopify_customer_id = fields.Char('Shopify Id', readonly=True)

    def sync_shopify_customer(self):
        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version

        customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
        api_key, PASSWORD, store_name, version)
        partner = self.env['res.partner'].search([('id', '=', self.id)])
        if not self.synced_customer:
            self.synced_customer = True
            payload = json.dumps({
                "customer": {
                    "first_name": self.name,
                    "last_name": "",
                    "email": self.email or '',
                    "verified_email": True,
                    "addresses": [
                        {
                            "address1": self.street,
                            "city": self.city,
                            "province": self.state_id.name or "",
                            "zip": self.zip,
                            "last_name": "",
                            "first_name": self.name,
                            "country": self.country_id.name or ''
                        }
                    ],
                    "send_email_invite": True
                }
            })
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", customer_url, headers=headers,
                                        data=payload)
            print('response', response)
