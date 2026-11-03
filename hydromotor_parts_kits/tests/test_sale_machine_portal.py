"""Real HTTP portal tests: standard sale authorization; no machine ACL grants."""
import json

from lxml import html
from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install', 'hm_sale_machine_portal')
class TestSaleMachinePortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sales = new_test_user(cls.env, login='hm_portal_sales', password='hm_portal_sales',
            groups='sales_team.group_sale_salesman',
            context={'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.customer = new_test_user(cls.env, login='hm_portal_customer', password='hm_portal_customer',
            groups='base.group_portal',
            context={'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.partner = cls.customer.partner_id
        cls.product = cls.env['product.product'].create({'name': 'Portal spare', 'type': 'consu'})
        machine_product = cls.env['product.product'].create({'name': 'Portal machine',
            'type': 'consu', 'is_storable': True, 'tracking': 'serial'})
        cls.machines = cls.env['x_hm_machine']
        for serial in ('HM-PORTAL-001', 'HM-PORTAL-002'):
            lot = cls.env['stock.lot'].create({'name': serial,
                'product_id': machine_product.id, 'company_id': cls.env.company.id})
            cls.machines |= cls.env['x_hm_machine'].create({'x_name': 'Portal Model',
                'x_model_label': 'Portal <safe> Model', 'x_lot_id': lot.id,
                'x_partner_id': cls.partner.id, 'x_company_id': cls.env.company.id,
                'x_notes': 'HM-PRIVATE-DOSSIER-NOTES'})
        cls.order = cls.env['sale.order'].create({'partner_id': cls.partner.id,
            'user_id': cls.sales.id, 'x_hm_order_machine_id': cls.machines[0].id,
            'order_line': [Command.create({'product_id': cls.product.id, 'name': 'Inherited spare'}),
                Command.create({'product_id': cls.product.id, 'name': 'Override spare',
                    'x_hm_parts_machine_id': cls.machines[1].id}),
                Command.create({'product_id': cls.product.id, 'name': 'Cleared spare',
                    'x_hm_parts_machine_id': False})]})

    def _page(self, order, token=None):
        path = '/my/orders/%s' % order.id
        if token is not None:
            path += '?access_token=' + token
        return self.url_open(path, allow_redirects=False,
            headers={'Odoo-Link-Preview': 'True'})

    def _assert_mixed(self, response):
        self.assertEqual(response.status_code, 200, response.text[:200])
        dom = html.fromstring(response.content)
        header = dom.xpath("//*[contains(@class,'hm-portal-machine-default')]")
        self.assertEqual(len(header), 1, 'Customer Preview is missing machine header')
        self.assertIn('HM-PORTAL-001', header[0].text_content())
        rows = dom.xpath("//tr[@name='tr_product']")
        self.assertEqual(len(rows), 3)
        self.assertIn('HM-PORTAL-001', rows[0].text_content())
        self.assertIn('HM-PORTAL-002', rows[1].text_content())
        self.assertFalse(rows[2].xpath(".//*[contains(@class,'hm-portal-machine-line')]"))
        self.assertIn('Portal <safe> Model', rows[1].text_content())
        self.assertFalse(dom.xpath('//safe'))
        self.assertNotIn('HM-PRIVATE-DOSSIER-NOTES', response.text)

    def test_internal_preview_renders_mixed_attribution(self):
        self.authenticate(self.sales.login, self.sales.login)
        self._assert_mixed(self._page(self.order))

    def test_public_token_renders_without_machine_read_acl(self):
        from odoo.exceptions import AccessError
        public = self.env.ref('base.public_user')
        self.assertFalse(self.machines.with_user(public).has_access('read'))
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.machines.with_user(public).read(['x_model_label', 'x_serial', 'x_notes'])
        token = self.order._portal_ensure_token()
        before = self.order.message_ids
        self.authenticate(None, None)
        self._assert_mixed(self._page(self.order, token))
        self.assertEqual(self.order.message_ids, before, 'Link preview must not post viewed note')

    def test_portal_owner_renders_without_machine_read_acl(self):
        self.assertFalse(self.machines.with_user(self.customer).has_access('read'))
        self.authenticate(self.customer.login, self.customer.login)
        self._assert_mixed(self._page(self.order))

    def test_portal_direct_machine_rpc_stays_denied(self):
        self.authenticate(self.customer.login, self.customer.login)
        response = self.url_open('/web/dataset/call_kw/x_hm_machine/read',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                'params': {'model': 'x_hm_machine', 'method': 'read',
                    'args': [self.machines.ids, ['x_model_label', 'x_serial', 'x_notes']],
                    'kwargs': {}}}), headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['error']['data']['name'], 'odoo.exceptions.AccessError')
        self.assertNotIn('HM-PORTAL-001', response.text)
        self.assertNotIn('HM-PRIVATE-DOSSIER-NOTES', response.text)

    def test_invalid_missing_and_other_order_tokens_disclose_nothing(self):
        other_partner = self.env['res.partner'].create({'name': 'Unrelated portal customer'})
        other = self.env['sale.order'].create({'partner_id': other_partner.id,
            'client_order_ref': 'HM-PRIVATE-OTHER-ORDER'})
        token = self.order._portal_ensure_token()
        self.authenticate(None, None)
        for order, supplied in ((self.order, None), (self.order, 'invalid-token'), (other, token)):
            response = self._page(order, supplied)
            self.assertEqual(response.status_code, 303)
            self.assertNotIn('HM-PORTAL-001', response.text)
            self.assertNotIn('HM-PRIVATE-OTHER-ORDER', response.text)
        self.authenticate(self.customer.login, self.customer.login)
        self.assertEqual(self._page(other).status_code, 303)
        self.assertEqual(self._page(other, token).status_code, 303)

    def test_no_machine_hides_header_and_all_line_blocks(self):
        self.order.write({'x_hm_order_machine_id': False})
        self.order.order_line.write({'x_hm_parts_machine_id': False})
        self.authenticate(None, None)
        response = self._page(self.order, self.order._portal_ensure_token())
        self.assertEqual(response.status_code, 200)
        dom = html.fromstring(response.content)
        self.assertFalse(dom.xpath("//*[contains(@class,'hm-portal-machine-')]"))
        self.assertNotIn('HM-PORTAL-001', response.text)

    def test_line_override_remains_without_header(self):
        self.order.x_hm_order_machine_id = False
        self.authenticate(None, None)
        response = self._page(self.order, self.order._portal_ensure_token())
        self.assertEqual(response.status_code, 200)
        dom = html.fromstring(response.content)
        self.assertFalse(dom.xpath("//*[contains(@class,'hm-portal-machine-default')]"))
        lines = dom.xpath("//*[contains(@class,'hm-portal-machine-line')]")
        self.assertEqual(len(lines), 1)
        self.assertIn('HM-PORTAL-002', lines[0].text_content())
