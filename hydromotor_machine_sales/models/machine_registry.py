"""Transactional bridge for existing XML/manual records (no replacement models).

Public entry points remain the existing group-restricted server actions.
This private service never commits; failures roll back sale/stock and dossiers.
"""
from odoo import api, models
from odoo.exceptions import AccessError, UserError


class MachineRegistryService(models.AbstractModel):
    _name = 'hydromotor.machine.registry'
    _description = 'Hydromotor machine dossier bridge'

    def _register_hook(self):
        super()._register_hook()
        if 'x_hm_bridge' not in self.env or 'x_hms_source_key' not in self.env['x_hm_machine']._fields:
            return  # owning manual models may be absent during uninstall
        # DDL only: never SQL business writes or automatic duplicate cleanup.
        # Existing duplicates deliberately fail upgrade, requiring reconciliation.
        self.env.cr.execute("""CREATE UNIQUE INDEX IF NOT EXISTS hm_bridge_source_unique
            ON x_hm_bridge (x_source_key)
            WHERE x_source_key IS NOT NULL AND x_source_key <> ''""")
        self.env.cr.execute("""CREATE UNIQUE INDEX IF NOT EXISTS hm_machine_source_unique
            ON x_hm_machine (x_hms_source_key)
            WHERE x_hms_source_key IS NOT NULL AND x_hms_source_key <> ''""")
        self.env.cr.execute("""CREATE UNIQUE INDEX IF NOT EXISTS hm_machine_company_lot_unique
            ON x_hm_machine (x_company_id, x_lot_id) WHERE x_lot_id IS NOT NULL""")

    @api.model
    def _register_delivered(self, order):
        order.ensure_one()
        order.check_access('read')
        if order.company_id.id not in self.env.companies.ids:
            raise AccessError('Изберете дружеството на продажбата.')
        if not self.env.user.has_group('hydromotor_service.group_service_user'):
            raise AccessError('Нужни са права за Машини и сервиз.')
        if order.state != 'sale':
            raise UserError('Доставката изисква потвърдена продажба.')
        order.check_access('write')
        order.write({'x_hm_sync_revision': order.x_hm_sync_revision + 1})
        order.flush_recordset(['x_hm_sync_revision'])
        movements = self.env['stock.move.line'].search([
            ('move_id.sale_line_id.order_id', '=', order.id), ('state', '=', 'done'),
            ('location_dest_id.usage', '=', 'customer'),
            ('location_id.usage', '!=', 'customer'), ('lot_id', '!=', False),
            ('quantity', '>', 0), ('company_id', '=', order.company_id.id),
        ]).sorted('id')
        result = []
        for movement in movements:
            line = movement.move_id.sale_line_id
            if not line.x_hm_config_id and not line.x_hm_release_id:
                continue  # native service action still handles ordinary machines
            if (movement.product_id != line.product_id or movement.quantity != 1
                    or movement.product_id.tracking != 'serial'
                    or movement.lot_id.product_id != line.product_id
                    or (movement.lot_id.company_id and movement.lot_id.company_id != order.company_id)):
                raise UserError('Доставката изисква един реален сериен номер за правилния артикул и фирма.')
            bridges = self.env['x_hm_bridge'].search([
                ('x_line_id', '=', line.id), ('x_company_id', '=', order.company_id.id),
                ('x_order_id', '=', order.id),
            ]).sorted('x_unit_number')
            if len(bridges) != int(line.x_hm_release_id.x_quantity):
                raise UserError('Липсват предварителни досиета. Синхронизирайте продажбата преди доставката.')
            candidates = []
            for bridge in bridges:
                if bridge.x_target_model != 'x_hm_machine' or bridge.x_release_id != line.x_hm_release_id:
                    raise UserError('Несъвместима връзка на доставката.')
                machine = self.env['x_hm_machine'].browse(bridge.x_target_id).exists()
                if (not machine or machine.x_company_id != order.company_id
                        or machine.x_sale_order_id != order
                        or machine.x_hms_source_key != bridge.x_source_key
                        or machine.x_partner_id.commercial_partner_id != order.partner_id.commercial_partner_id):
                    raise UserError('Досието не съответства на доставката.')
                candidates.append(machine)
            same = [m for m in candidates if m.x_lot_id == movement.lot_id]
            if same:
                machine = same[0]
            else:
                conflict = self.env['x_hm_machine'].search([
                    ('x_lot_id', '=', movement.lot_id.id), ('x_company_id', '=', order.company_id.id)])
                if conflict:
                    raise UserError('Серийният номер вече има друго досие; не се обединява автоматично.')
                pending = [m for m in candidates if not m.x_lot_id]
                if not pending:
                    raise UserError('Доставените серийни номера надвишават броя предварителни досиета.')
                machine = pending[0]
                machine.write({
                    'x_lot_id': movement.lot_id.id,
                    'x_delivery_id': movement.picking_id.id,
                    'x_delivery_date': movement.picking_id.date_done.date() if movement.picking_id.date_done else False,
                    'x_hms_order_state': order.state,
                })
            if machine.id not in result:
                result.append(machine.id)
        return result

    @api.model
    def _sync_order(self, order):
        order.ensure_one()
        order.check_access('write')
        if order.company_id.id not in self.env.companies.ids:
            raise AccessError('Изберете дружеството на продажбата.')
        lines = order.order_line.filtered(lambda l: l.x_hm_config_id or l.x_hm_release_id)
        bridges = self.env['x_hm_bridge']
        domain = [('x_order_id', '=', order.id), ('x_company_id', '=', order.company_id.id)]
        if not lines and not bridges.search(domain):
            return
        if not self.env.user.has_group('hydromotor_service.group_service_user'):
            raise AccessError('Нужни са права за Машини и сервиз; не се заобикалят ACL.')
        # A real UPDATE, not SELECT/advisory lock: concurrent REPEATABLE READ
        # transactions conflict and Odoo retries the entire request with a fresh
        # snapshot. This existing field is excluded from sale_sync triggers.
        order.write({'x_hm_sync_revision': order.x_hm_sync_revision + 1})
        order.flush_recordset(['x_hm_sync_revision'])
        links = bridges.search(domain)
        for link in links:
            if link.x_target_model != 'x_hm_machine':
                raise UserError('Поддържа се само съществуващото сервизно досие x_hm_machine.')
            machine = self.env['x_hm_machine'].browse(link.x_target_id).exists()
            if not machine or machine.x_company_id != order.company_id:
                raise UserError('Липсва досие или е от друго дружество; възстановете връзката.')
            if machine.x_hms_source_key != link.x_source_key:
                raise UserError('Променен източник на досието.')
            if machine.x_sale_order_id != order:
                raise UserError('Досието е свързано с друга продажба.')
            machine.write({'x_hms_order_state': order.state})
        if order.state != 'sale':
            return
        settings = self.env['x_hm_settings'].search([('x_company_id', '=', order.company_id.id)])
        if len(settings) != 1 or not settings.x_enabled:
            raise UserError('Активирайте връзката в Машини → Настройки за това дружество.')
        if settings.x_target_model_id.model != 'x_hm_machine':
            raise UserError('Връзката изисква модела x_hm_machine.')
        machines = self.env['x_hm_machine'].with_company(order.company_id)
        for line in lines:
            if line.product_id.tracking != 'serial':
                raise UserError('За продажба на машина е необходимо проследяване по сериен номер.')
            release = line.x_hm_release_id
            if not release or not line.x_hm_config_id or release.x_config_id != line.x_hm_config_id:
                raise UserError('Липсва фиксирана конфигурация за реда.')
            qty = release.x_quantity
            if qty < 1 or qty != int(qty):
                raise UserError('Броят машини трябва да е положително цяло число.')
            for number in range(1, int(qty) + 1):
                key = 'HM/SOL/%s/%s' % (line.id, number)
                existing = bridges.search([('x_source_key', '=', key)])
                if len(existing) > 1:
                    raise UserError('Повторена вътрешна връзка: ' + key)
                if existing:
                    if (existing.x_release_id != release or existing.x_company_id != order.company_id
                            or existing.x_order_id != order or existing.x_line_id != line):
                        raise UserError('Връзката е за друга продажба или конфигурация: ' + key)
                    continue
                machine = machines.search([('x_hms_source_key', '=', key)])
                if len(machine) > 1:
                    raise UserError('Повторен източник в регистъра: ' + key)
                if machine:
                    if (machine.x_company_id != order.company_id
                            or machine.x_sale_order_id != order
                            or machine.x_partner_id.commercial_partner_id != order.partner_id.commercial_partner_id):
                        raise UserError('Съществуващото досие не съответства на продажбата.')
                else:
                    machine = machines.with_context(mail_create_nosubscribe=True).create({
                        'x_name': '%s — %s / %s' % (release.x_product_id.name, order.name, number),
                        'x_company_id': order.company_id.id,
                        'x_partner_id': order.partner_id.commercial_partner_id.id,
                        'x_sale_order_id': order.id, 'x_hms_source_key': key,
                        'x_hms_order_state': order.state,
                        'x_hms_quote_description': release.x_description,
                        # x_product_id/x_serial are readonly related fields:
                        # never assign a fake lot just to populate them.
                        'x_model_label': release.x_product_id.name,
                    })
                # ONLY this internal link insert is elevated: sales/service ACLs
                # deliberately allow read but not direct bridge writes. All
                # source/target access and company validation above use caller ACL.
                bridges.sudo().create({
                    'x_name': machine.x_name, 'x_source_key': key,
                    'x_order_id': order.id, 'x_line_id': line.id,
                    'x_config_id': release.x_config_id.id, 'x_release_id': release.id,
                    'x_company_id': order.company_id.id,
                    'x_target_model': 'x_hm_machine', 'x_target_id': machine.id,
                    'x_unit_number': number, 'x_state_field': 'x_hms_order_state',
                })
