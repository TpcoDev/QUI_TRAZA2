# -*- coding: utf-8 -*-

import logging

from psycopg2 import Error, OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # unit_ref
    unit_ref = fields.Char(string='Unit.',compute="compute_unit")
    cant = fields.Float(string='Cant.',required=False,compute="compute_cant")


    @api.depends('quantity')
    def compute_cant(self):
        for record in self:
            self.cant=record.inventory_quantity/record.product_uom_id.factor

    @api.depends('product_id')
    def compute_unit(self):
        uom_all= self.env['uom.uom'].search([])
        for record in self:
            oum_obj=uom_all.filtered(lambda uo: uo.id==record.product_uom_id.id and uo.uom_type=="reference")
            record.unit_ref=oum_obj.name




