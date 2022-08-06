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


class ProductWizard(models.TransientModel):
    _name = 'product.wizard'
    _description = 'Product Wizard'

    import_products = fields.Selection(string='Import/Export',
                                       selection=[('shopify', 'To Shopify'),
                                                  ('odoo', 'From Shopify')],
                                       required=True, default='odoo')
    shopify_instance_id = fields.Many2one('shopify.configuration',
                                          string="Shopify Instance",
                                          required=True)

    def sync_products(self):
        shopify_instance = self.shopify_instance_id
        api_key = self.shopify_instance_id.con_endpoint
        PASSWORD = self.shopify_instance_id.consumer_key
        store_name = self.shopify_instance_id.shop_name
        version = self.shopify_instance_id.version

        if self.import_products == 'shopify':
            product_url = "https://%s:%s@%s/admin/api/%s/products.json" % (
                api_key, PASSWORD, store_name, version)
            product = self.env['product.template'].search([])
            for rec in product:
                if not rec.synced_product:
                    rec.synced_product = True
                    variants = []
                    for line in rec.attribute_line_ids.value_ids:
                        line_vals = {
                            "option1": line.name,
                            "price": rec.list_price,
                            "sku": rec.qty_available
                        }
                        variants.append(line_vals)
                    product_attribute = self.env['product.attribute']
                    options = []
                    for line in rec.attribute_line_ids:
                        vals = {
                            "name": line.attribute_id.name,
                            "values": variants
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
        else:
            product_url = "https://%s:%s@%s/admin/api/%s/products.json" % (
                api_key, PASSWORD, store_name, version)
            payload = []
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.request("GET", product_url,
                                        headers=headers,
                                        data=payload)
            j = response.json()
            shopify_products = j['products']
            product_link = response.headers[
                'link'] if 'link' in response.headers else ''
            product_links = product_link.split(',')
            for link in product_links:
                match = re.compile(r'rel=\"next\"').search(link)
                if match:
                    product_link = link
            rel = re.search('rel=\"(.)\"', product_link).group(
                1) if 'link' in response.headers else ''
            if product_link and rel == 'next':
                i = 0
                n = 1
                while i < n:
                    page_info = re.search('page_info=(.*)>',
                                          product_link).group(1)
                    limit = re.search('limit=(.*)&', product_link).group(1)
                    product_link = "https://%s:%s@%s/admin/api/%s/products.json?limit=%s&page_info=%s" % (
                        api_key, PASSWORD, store_name, version, limit,
                        page_info)
                    response = requests.request('GET', product_link,
                                                headers=headers, data=payload)
                    j = response.json()
                    products = j['customers']
                    shopify_products += products
                    product_link = response.headers['link']
                    product_links = product_link.split(',')
                    for link in product_links:
                        match = re.compile(r'rel=\"next\"').search(link)
                        if match:
                            product_link = link
                    rel = re.search('rel=\"next\"', product_link)
                    i += 1
                    if product_link and rel is not None:
                        n += 1
            for product in shopify_products:
                exist_products = self.env['product.template'].search(
                    [('shopify_product_id', '=', product['id']),
                     ('shopify_instance', '=', shopify_instance.id)])
                if not exist_products:
                    if product['options']:
                        for option in product['options']:
                            attribute_id = self.env[
                                'product.attribute'].sudo().search([
                                ('shopify_attribute_id', '=', option['id']),
                                ('shopify_instance_id', '=',
                                 shopify_instance.id)
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
                                        attribute_id.sudo().write({
                                            'value_ids': [(0, 0, att_val)]
                                        })
                            else:
                                attribute_id = self.env[
                                    'product.attribute'].sudo().create({
                                    'name': option['name'],
                                    'shopify_attribute_id': option['id'],
                                    'shopify_instance_id': shopify_instance.id,

                                })
                                for opt_val in option['values']:
                                    att_val = {
                                        'name': opt_val
                                    }
                                    attribute_id.sudo().write({
                                        'value_ids': [(0, 0, att_val)]
                                    })
                    product_id = self.env['product_template'].sudo().create({
                        'name': product['title'],
                        'type': 'product',
                        'categ_id': self.env.ref(
                            'product.product_category_all').id,
                        'synced_product': True,
                        'description': product['body_html'],
                        'shopify_product_id': product['id'],
                        'shopify_instance_id': shopify_instance.id,
                        'company_id': shopify_instance.company_id.id,
                    })
                    if product['options']:
                        for option in product['option']:
                            attribute_id = self.env[
                                'product.attribute'].sudo().search([
                                ('shopify_attribute_id', '=', option['id']),
                                (
                                    'shopify_instance_id', '=',
                                    shopify_instance.id)
                            ])
                            att_val_ids = self.env[
                                'product_attribute.value'].sudo().search([
                                ('name', 'in', option['values']),
                                ('attribute_id', '=', attribute_id.id)
                            ])
                            att_line = {
                                'attribute_id': attribute_id.id,
                                'value_ids': [(4, att_val.id) for att_val in
                                              att_val_ids]
                            }
                            product_id.sudo().write({
                                'attribute_line_ids': [(0, 0, att_line)]
                            })
                        for shopify_var in product['variants']:
                            shopify_var_list = []
                            shopify_var_id_list = []
                            r = 3
                            for i in range(1, r):
                                if shopify_var['option' + str(i)] is not None:
                                    shopify_var_list.append(
                                        shopify_var['option' + str(i)])
                                else:
                                    break
                            for option in product['options']:
                                for var in shopify_var_list:
                                    if var in option['values']:
                                        attribute_id = self.env[
                                            'product.attribute'].sudo().search(
                                            [
                                                ('shopify_attrbute_id', '=',
                                                 option['id']),
                                                ('shopify_instance_id', '=',
                                                 shopify_instance.id)
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
                                        'shopify_instance_id': shopify_instance.id,
                                        'synced_product': True,
                                        'company_id': shopify_instance.company_id.id,
                                        'default_code': shopify_var['sku'],
                                    })
                    else:
                        for variant in product_id.product_variant_ids:
                            variant.sudo().write({
                                'shopify_variant_id': product['id'],
                                'shopify_instance_id': shopify_instance.id,
                                'synced_product': True,
                                'company_id': shopify_instance.company_id.id,
                            })
