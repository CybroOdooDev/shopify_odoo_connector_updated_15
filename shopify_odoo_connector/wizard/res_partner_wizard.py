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
import re
from odoo import models, fields
import requests
import json


class CustomerWizard(models.TransientModel):
    _name = 'customer.wizard'
    _description = 'Customer Wizard'

    import_customers = fields.Selection(string='Import/Export',
                                        selection=[('shopify', 'To Shopify'),
                                                   ('odoo', 'From Shopify')],
                                        required=True, default='odoo')
    shopify_instance_id = fields.Many2one('shopify.configuration',
                                       string="Shopify Instance", required=True)

    def sync_customers(self):
        shopify_instance = self.shopify_instance_id
        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version

        if self.import_customers == 'shopify':
            customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
                api_key, PASSWORD, store_name, version)
            partner = self.env['res.partner'].search([])
            for customer in partner:
                if not customer.synced_customer:
                    customer.synced_customer = True
                    payload = json.dumps({
                        "customer": {
                            "first_name": customer.name,
                            "last_name": "",
                            "email": customer.email or '',
                            "verified_email": True,
                            "addresses": [
                                {
                                    "address1": customer.street,
                                    "city": customer.city,
                                    "province": customer.state_id.name or '',
                                    "zip": customer.zip,
                                    "last_name": "",
                                    "first_name": customer.name,
                                    "country": customer.country_id.name or ''
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
        else:
            customer_url = "https://%s:%s@%s/admin/api/%s/customers.json" % (
                api_key, PASSWORD, store_name, version)
            payload = []
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.request("GET", customer_url,
                                        headers=headers,
                                        data=payload)
            j = response.json()
            shopify_customers = j['customers']
            customer_link = response.headers[
                'link'] if 'link' in response.headers else ''
            customer_links = customer_link.split(',')
            for link in customer_links:
                match = re.compile(r'rel=\"next\"').search(link)
                if match:
                    customer_link = link
            rel = re.search('rel=\"(.)\"', customer_link).group(
                1) if 'link' in response.headers else ''
            if customer_link and rel == 'next':
                i = 0
                n = 1
                while i < n:
                    page_info = re.search('page_info=(.*)>',
                                          customer_link).group(1)
                    limit = re.search('limit=(.*)&', customer_link).group(1)
                    customer_link = "https://%s:%s@%s/admin/api/%s/customers.json?limit=%s&page_info=%s" % (
                        api_key, PASSWORD, store_name, version, limit,
                        page_info)
                    response = requests.request('GET', customer_link,
                                                headers=headers, data=payload)
                    j = response.json()
                    customers = j['customers']
                    shopify_customers += customers
                    customer_link = response.headers['link']
                    customer_links = customer_link.split(',')
                    for link in customer_links:
                        match = re.compile(r'rel=\"next\"').search(link)
                        if match:
                            customer_link = link
                    rel = re.search('rel=\"next\"', customer_link)
                    i += 1
                    if customer_link and rel is not None:
                        n += 1
            for customer in shopify_customers:
                exist_customers = self.env['res.partner'].search(
                    [('shopify_customer_id', '=', customer['id']),
                     ('shopify_instance_id', '=', shopify_instance.id)])
                if not exist_customers:
                    vals = {}
                    if customer['first_name']:
                        vals['name'] = customer['first_name']
                    if customer['last_name']:
                        if customer['first_name']:
                            vals['name'] = customer['first_name'] + ' ' + \
                                           customer['last_name']
                        else:
                            vals['naem'] = customer['last_name']
                    if not customer['first_name'] and not customer[
                        'last_name'] and customer['email']:
                        vals['name'] = customer['email']
                    vals['email'] = customer['email']
                    vals['phone'] = customer['phone']
                    vals['shopify_customer_id'] = customer['id']
                    vals['shopify_instance_id'] = shopify_instance.id
                    vals['synced_customer'] = True
                    vals['company_id'] = shopify_instance.company_id.id
                    if customer['addresses']:
                        country_id = self.env['res.country'].sudo().search([
                            ('name', '=', customer['addresses'][0]['country'])
                        ])
                        state_id = self.env['res.country.state'].sudo().search([
                            ('name', '=', customer['addresses'][0]['province'])
                        ])
                        vals = {
                            'street': customer['addresses'][0]['address1'],
                            'street2': customer['addresses'][0]['address2'],
                            'city': customer['addresses'][0]['city'],
                            'country_id': country_id.id if country_id else '',
                            'state_id': state_id.id if state_id else '',
                            'zip': customer['addresses'][0]['zip'],
                        }
                    self.env['res.partner'].sudo().create(vals)
                else:
                    vals = {}
                    if customer['first_name']:
                        vals['name'] = customer['first_name']
                    if customer['last_name']:
                        if customer['first_name']:
                            vals['name'] = customer['first_name'] + ' ' + \
                                           customer['last_name']
                        else:
                            vals['naem'] = customer['last_name']
                    if not customer['first_name'] and not customer[
                        'last_name'] and customer['email']:
                        vals['name'] = customer['email']
                    vals['email'] = customer['email']
                    vals['phone'] = customer['phone']
                    vals['shopify_customer_id'] = customer['id']
                    vals['shopify_instance_id'] = shopify_instance.id
                    vals['synced_customer'] = True
                    vals['company_id'] = shopify_instance.company_id.id
                    if customer['addresses']:
                        country_id = self.env['res.country'].sudo().search([
                            ('name', '=', customer['addresses'][0]['country'])
                        ])
                        state_id = self.env['res.country.state'].sudo().search([
                            ('name', '=', customer['addresses'][0]['province'])
                        ])
                        vals = {
                            'street': customer['addresses'][0]['address1'],
                            'street2': customer['addresses'][0]['address2'],
                            'city': customer['addresses'][0]['city'],
                            'country_id': country_id.id if country_id else '',
                            'state_id': state_id.id if state_id else '',
                            'zip': customer['addresses'][0]['zip'],
                        }
                    self.env['res.partner'].sudo().write(vals)
