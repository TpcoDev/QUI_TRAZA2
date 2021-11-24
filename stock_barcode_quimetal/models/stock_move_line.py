import base64
import logging
from io import BytesIO

import barcode
from barcode.writer import ImageWriter

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Lines(models.Model):
    _name = 'stock.quimetal.lines'

    line_id = fields.Many2one(comodel_name='stock.move.line', string='Line')
    num_bultos = fields.Integer(string='Numero de Bultos', required=False)
    cant_envases = fields.Integer(string='Cantidad de Envases')
    peso_envase = fields.Float(string='Peso/Envase', required=False)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    _description = 'Description'

    quimetal_lines_ids = fields.One2many(
        comodel_name='stock.quimetal.lines', inverse_name='line_id',
        string='Quimetal lines', required=False
    )

    total_cant_envases = fields.Integer(compute='_compute_total_cant_envases', string='Total Cantidad de Envases')
    total_peso_envase = fields.Float(compute='_compute_total_peso_envase', string='Total Peso/Envase')

    @api.depends('quimetal_lines_ids.cant_envases')
    def _compute_total_cant_envases(self):
        for rec in self:
            rec.total_cant_envases = sum(rec.quimetal_lines_ids.mapped('cant_envases'))

    @api.depends('quimetal_lines_ids.peso_envase', 'quimetal_lines_ids.cant_envases', 'quimetal_lines_ids.num_bultos')
    def _compute_total_peso_envase(self):
        sum_list = []
        for rec in self:
            for line in rec.quimetal_lines_ids:
                sum_list.append(line.peso_envase * line.cant_envases * line.num_bultos)
            rec.total_peso_envase = sum(sum_list)

    def export_pdf(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        tipos = 1 if self.product_id.as_type_product == 'MP' else 0
        as_cantidades = 67

        calculo = datos_producto.as_contenido_envase * datos_producto.as_cantidad_envase * datos_producto.as_cantidad_unidades
        kg_compra = move.qty_done
        if calculo > 0:
            total = kg_compra / calculo
        else:
            total = kg_compra
        total = math.ceil(total)


        datas['model'] = 'as.wizard.formulas'
        datas['form'] = self.read()[0]
        diccionario = []
        # tipo 1 move
        if tipos == 1:
            file_like_object = BytesIO()
            EAN = barcode.get_barcode_class('code128')
            ean = EAN(self.as_barcode_mpp_1_CDB(), writer=ImageWriter())
            ean.write(file_like_object, options={"write_text": False})
            self.as_imge = base64.b64encode(file_like_object.getvalue())
            for i in range(0, as_cantidades):
                diccionario.append(self.id)
            if diccionario == []:
                raise UserError("Debe guardar el formulario para generar reporte")
            return self.env.ref('as_stock_equimetal.as_reporte_2').report_action(diccionario)
        else:
            file_like_object = BytesIO()
            EAN = barcode.get_barcode_class('code128')
            ean = EAN(self.as_barcode_pp_1_CDB(), writer=ImageWriter())
            ean.write(file_like_object, options={"write_text": False})
            self.as_imge = base64.b64encode(file_like_object.getvalue())
            for i in range(0, as_cantidades):
                diccionario.append(self.id)

            if diccionario == []:
                raise UserError("Debe guardar el formulario para generar reporte")
            return self.env.ref('as_stock_equimetal.as_reportes_etiquetas_pdf').report_action(diccionario)
