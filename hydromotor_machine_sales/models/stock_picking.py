"""Assign real serials only once the standard stock completion has succeeded."""
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        result = super()._action_done()
        delivered = self.move_line_ids.filtered(
            lambda ml: ml.state == 'done' and ml.location_dest_id.usage == 'customer'
            and ml.location_id.usage != 'customer'
            and (ml.move_id.sale_line_id.x_hm_config_id or ml.move_id.sale_line_id.x_hm_release_id)
        )
        orders = delivered.mapped('move_id.sale_line_id.order_id').sorted('id')
        for order in orders:
            self.env['hydromotor.machine.registry']._register_delivered(order)
        return result
