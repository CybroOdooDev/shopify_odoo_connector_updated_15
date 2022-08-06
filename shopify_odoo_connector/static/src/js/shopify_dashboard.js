odoo.define('ShopifyDashboard.ShopifyDashboard', function(require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var ActionMenu = AbstractAction.extend({
        contentTemplate: 'ShopifyDashboard',
        events: {
            'click .shopify_dashboard': 'onclick_dashboard',
        },

    });
    core.action_registry.add('shopify_dashboard', ActionMenu);
});