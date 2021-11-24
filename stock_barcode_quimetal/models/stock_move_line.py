import base64
import logging
from io import BytesIO

import barcode
from barcode.writer import ImageWriter

from odoo import models, fields
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

    def export_pdf(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        tipos = self._context.get('tipo')
        datas['model'] = 'as.wizard.formulas'
        datas['form'] = self.read()[0]
        diccionario = []
        # tipo 1 move
        if self._context.get('tipo') == 1:
            for contexto_lotes in self.wiz_lineas:
                if self.modelo != "stock.production.lot":
                    file_like_object = BytesIO()
                    EAN = barcode.get_barcode_class('code128')
                    ean = EAN(contexto_lotes.operacion_id.as_barcode_mpp_1_CDB(), writer=ImageWriter())
                    ean.write(file_like_object, options={"write_text": False})
                    contexto_lotes.operacion_id.as_imge = base64.b64encode(file_like_object.getvalue())
                    for i in range(0, contexto_lotes.as_cantidades):
                        diccionario.append(contexto_lotes.operacion_id.id)
                else:
                    move_id = self.env['stock.move.line'].search([('lot_id', '=', contexto_lotes.lots_id.id)],
                                                                 order='date asc', limit=1)
                    if not move_id:
                        raise UserError("El producto no posee Stock")
                    file_like_object = BytesIO()
                    EAN = barcode.get_barcode_class('code128')
                    ean = EAN(move_id.as_barcode_mpp_1_CDB(), writer=ImageWriter())
                    ean.write(file_like_object, options={"write_text": False})
                    move_id.as_imge = base64.b64encode(file_like_object.getvalue())
                    for i in range(0, contexto_lotes.as_cantidades):
                        diccionario.append(move_id.id)
            if diccionario == []:
                raise UserError("Debe guardar el formulario para generar reporte")
            return self.env.ref('as_stock_equimetal.as_reporte_2').report_action(diccionario)
        else:
            for contexto_lotes in self.wiz_lineas:
                if self.modelo != "stock.production.lot":
                    file_like_object = BytesIO()
                    EAN = barcode.get_barcode_class('code128')
                    ean = EAN(contexto_lotes.operacion_id.as_barcode_pp_1_CDB(), writer=ImageWriter())
                    ean.write(file_like_object, options={"write_text": False})
                    contexto_lotes.operacion_id.as_imge = base64.b64encode(file_like_object.getvalue())

                    for i in range(0, contexto_lotes.as_cantidades):
                        diccionario.append(contexto_lotes.operacion_id.id)
                else:
                    move_id = self.env['stock.move.line'].search([('lot_id', '=', contexto_lotes.lots_id.id)],
                                                                 order='date asc', limit=1)
                    if not move_id:
                        raise UserError("El producto no posee Stock")
                    file_like_object = BytesIO()
                    EAN = barcode.get_barcode_class('code128')
                    ean = EAN(move_id.as_barcode_pp_1_CDB(), writer=ImageWriter())
                    ean.write(file_like_object, options={"write_text": False})
                    move_id.as_imge = base64.b64encode(file_like_object.getvalue())
                    for i in range(0, contexto_lotes.as_cantidades):
                        diccionario.append(move_id.id)

            if diccionario == []:
                raise UserError("Debe guardar el formulario para generar reporte")
            return self.env.ref('as_stock_equimetal.as_reportes_etiquetas_pdf').report_action(diccionario)
