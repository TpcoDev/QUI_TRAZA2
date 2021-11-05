# -*- coding: utf-8 -*-
from odoo.tools.translate import _
from odoo import http
from odoo import http
from odoo.http import request
from datetime import datetime
from bs4 import BeautifulSoup
import json
import sys
import uuid
from odoo import http
from odoo.http import request, Response
import jsonschema
from jsonschema import validate
import json
import yaml
import requests, json
from . import as_estructuras
import logging
_logger = logging.getLogger(__name__)
from datetime import timedelta, datetime, date
import calendar
from dateutil.relativedelta import relativedelta
import os.path
from werkzeug import urls
from werkzeug.wsgi import wrap_file
address_api = {
    'WS005':'/api/Trazabilidad/ProductoRecibido',
    'WS004':'/api/Trazabilidad/TransferenciaSF',
    'WS006':'/api/Trazabilidad/SalidaMMPP',
    'WS099':'/api/Trazabilidad/RecepcionBodegaDespacho',
    'WS018':'/api/Trazabilidad/ActualizacionDespacho',
    'WS021':'/api/Trazabilidad/DevolucionClientes',
}
class as_webservice_quimetal(http.Controller):

    # WS001, de SAP a ODOO
    @http.route(['/tpco/odoo/ws001',], auth="public", type="json", method=['POST'], csrf=False)
    def WS001(self, **post):
        post = yaml.load(request.httprequest.data)
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OC recibidas correctamente"				
            }
        try:
            myapikey = request.httprequest.headers.get("Authorization")
            if not myapikey:
                self.create_message_log("ws001",as_token,post,'RECHAZADO','API KEY no existe')
                return mensaje_error
            user_id = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=myapikey)
            request.uid = user_id
            if user_id:
                res['token'] = as_token
                post = post['params']
                uid = user_id
                # request.session.logout()
                estructura = self.get_file('ws001.json')
                # es_valido = True
                es_valido = self.validar_json(post, esquema=estructura)

                if es_valido:
                    # Tratamiento de cliente
                    w_search = request.env["purchase.order"].sudo().search([('name', '=', post['DocNum'])],limit=1)
                    if not w_search:
                        cliente = request.env['res.partner']
                        cliente_search = cliente.sudo().search([('vat', '=', post['CardCode'])],limit=1)
                        if cliente_search.id:
                            cliente_id = cliente_search.id
                        else:
                            cliente_nuevo = cliente.sudo().create(
                                {
                                    "name": post['CardName'],
                                    "vat": post['CardCode'],
                                    "l10n_latam_identification_type_id": 2,
                                    "company_type": 'company',
                                }
                            )
                            cliente_id = cliente_nuevo.id

                        # Orden de compra
                        compra = request.env['purchase.order']
                        date_order = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        date_approve = post['DocDate'].replace("T"," ")[:-3]

                        compra_nueva_linea = []
                        for linea in post["DatosProdOC"]:
                            producto_uom = request.env['uom.uom']
                            producto_uom_search = producto_uom.sudo().search([('name', '=', linea['MeasureUnit'])])[0]
                            producto_uom_id = 0
                            if producto_uom_search.id:
                                producto_uom_id = producto_uom_search.id
                            # Tratamiento de producto
                            producto = request.env['product.template']
                            producto_search = producto.sudo().search([('default_code', '=', linea['ItemCode'])])
                            if producto_search.id:
                                producto_id = producto_search.id
                                product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
                                product_product_id = product_product.id
                            else:
                                product_data = {
                                    "name": str(linea['ItemDescription']) or "",
                                    "categ_id": 1,
                                    "default_code": str(linea['ItemCode']) or "",
                                    "barcode": "",
                                    "uom_id": producto_uom_id,
                                    "uom_po_id": producto_uom_id,
                                    "type": "product",
                                    "use_expiration_date": True,
                                    "list_price": 1,
                                    "tracking": 'lot',
                                    "standard_price": 0,
                                    "purchase_ok": True,
                                    "sale_ok": True,
                                }
                                _logger.debug("\n\n\n\n\nproduct_data: %s", product_data)
                                producto_nuevo = producto.sudo().create(product_data)
                                producto_id = producto_nuevo.id
                                product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
                                product_product_id = product_product.id
                            compra_nueva_linea.append(
                                                        {
                                                        'display_type': False,
                                                        "product_id": product_product_id,
                                                        "product_qty": linea["Quantity"],
                                                        # "sequence": 1,
                                                        'name': linea["ItemDescription"],
                                                        'account_analytic_id': False,
                                                        'product_uom': producto_uom_id,
                                                        "price_unit":1,
                                                        "qty_received_manual":0,
                                                        # "date_planned":"2021-04-21 10:00:00",
                                                        "taxes_id":[[6,False,[]]],
                                                        "analytic_tag_ids":[
                                                        [6,False,[]]],} )
                        # request.env.cr.commit()
                        _logger.debug("\n\n\n\n\ncompra_nueva_linea: %s", compra_nueva_linea)

                        # Ensamblando la compra
                        compra_nueva = {
                            'name': post['DocNum'], 
                            'origin': post['DocNum'],
                            'priority': '0', 
                            'partner_id': cliente_id, 
                            'partner_ref': False, 
                            'currency_id': 2, 
                            'date_order': date_order,
                            'date_approve': date_approve, 
                            # 'date_planned': '2021-04-23 10:00:00', 
                            'receipt_reminder_email': False, 
                            'reminder_date_before_receipt': 1, 
                            'notes': post['CardCode'], 
                            'user_id': uid,
                            'company_id': 1, 
                            'payment_term_id': 7, 
                            'fiscal_position_id': False,
                            'order_line': [(0, False, line) for line in compra_nueva_linea],
                            }

                        nueva_compra = request.env['purchase.order'].sudo().create(compra_nueva)
                        nueva_compra.button_confirm()
                        self.create_message_log("ws001",as_token,post,'ACEPTADO','OC recibidas correctamente')
                        return mensaje_correcto
                    else:
                        self.create_message_log("ws001",as_token,post,'RECHAZADO','Ya existe el registro que pretende almacenar')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws001",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws001",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws001",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    # WS016, de SAP a ODOO
    @http.route(['/tpco/odoo/ws016',], auth="public", type="json", method=['POST'], csrf=False)
    def WS016(self, **post):
        post = yaml.load(request.httprequest.data)
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OV recibidas correctamente"				
            }
        try:
            myapikey = request.httprequest.headers.get("Authorization")
            if not myapikey:
                self.create_message_log("ws016",as_token,post,'RECHAZADO','API KEY no existe')
                return mensaje_error
            user_id = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=myapikey)
            request.uid = user_id
            if user_id:
                res['token'] = as_token
                uid = user_id
                # request.session.logout()
                estructura = self.get_file('ws016.json')
                es_valido = self.validar_json(post, esquema=estructura)
                # es_valido = True
                post = post['params']
                uid = request.env.user.id
                if es_valido:
                    w_search = request.env["sale.order"].sudo().search([('name', '=', post['DocNum'])],limit=1)
                    if not w_search:
                        # Tratamiento de cliente
                        cliente = request.env['res.partner']
                        cliente_search = cliente.sudo().search([('vat', '=', post['CardCode'])],limit=1)
                        if cliente_search.id:
                            cliente_id = cliente_search.id
                        else:
                            cliente_nuevo = cliente.sudo().create(
                                {
                                    "name": post['CardName'],
                                    "vat": post['CardCode'],
                                    "l10n_latam_identification_type_id": 2,
                                    "company_type": 'company',
                                }
                            )
                            cliente_id = cliente_nuevo.id

                        # Orden de venta
                        venta = request.env['sale.order']
                        date_order = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        date_approve = post['DocDate'].replace("T"," ")[:-3]
                        venta_nueva_linea = []
                        for linea in post["DatosProdOV"]:

                            # Tratamiento de producto
                            producto = request.env['product.template']
                            producto_search = producto.sudo().search([('default_code', '=', linea['ItemCode'])])
                            if producto_search.id:
                                producto_id = producto_search.id
                                product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
                                product_product_id = product_product.id
                            else:
                                product_data = {
                                    "name": str(linea['ItemDescription']) or "",
                                    "type": "product",
                                    "categ_id": 1,
                                    "default_code": str(linea['ItemCode']) or "",
                                    "barcode": "",
                                    "list_price": 1,
                                    "standard_price": 0,
                                    "uom_id": 3,
                                    "tracking": 'lot',
                                    "uom_po_id": 3,
                                    "purchase_ok": True,
                                    "sale_ok": True,
                                }

                                _logger.debug("\n\n\n\n\nproduct_data: %s", product_data)

                                producto_nuevo = producto.sudo().create(product_data)
                                producto_id = producto_nuevo.id
                                product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
                                product_product_id = product_product.id

                            # Tratamiento de UOM
                            producto_uom = request.env['uom.uom']
                            producto_uom_search = producto_uom.sudo().search([('name', '=', linea['MeasureUnit'])])[0]
                            producto_uom_id = 0
                            if producto_uom_search.id:
                                producto_uom_id = producto_uom_search.id

                            venta_nueva_linea.append(
                                                        {
                                                        'display_type': False,
                                                        "product_id": product_product_id,
                                                        "product_uom_qty": linea["Quantity"],
                                                        # "sequence": 1,
                                                        'name': linea["ItemDescription"],
                                                        # 'account_analytic_id': False,
                                                        'product_uom': producto_uom_id,
                                                        "price_unit":1,
                                                        "route_id":False,
                                                        "customer_lead":0,
                                                        "product_packaging":False,
                                                        "qty_delivered_manual":0,
                                                        "product_template_id":producto_id,

                                                        }
                                                    )
                        # request.env.cr.commit()
                        _logger.debug("\n\n\n\n\nventa_nueva_linea: %s", venta_nueva_linea)

                        # Ensamblando la venta
                        venta_nueva = {
                            'name': post['DocNum'], 
                            'origin': post['DocNum'],
                            'as_num_comex': post['NumAtcard'],
                            # 'priority': '0', 
                            'partner_id': cliente_id, 
                            # 'partner_ref': False, 
                            'currency_id': 2, 
                            'date_order': date_approve,
                            'user_id': uid,
                            'company_id': 1, 
                            'payment_term_id': 7, 
                            "fiscal_position_id":False,
                            "analytic_account_id":False,
                            "warehouse_id":1,
                            "incoterm":False,
                            "picking_policy":"direct",
                            "commitment_date":False,
                            "campaign_id":False,
                            "medium_id":False,
                            "source_id":False,
                            "signed_by":False,
                            "signed_on":False,
                            "signature":False,
                            "note":"",
                            "team_id":1,
                            "require_signature":True,
                            "require_payment":True,
                            "client_order_ref":False,
                            "show_update_pricelist":False,
                            "pricelist_id":1,
                            "partner_invoice_id":cliente_id,
                            "partner_shipping_id":cliente_id,
                            "sale_order_template_id":False,
                            "validity_date":False,
                            'order_line': [(0, False, line) for line in venta_nueva_linea],
                            }

                        nueva_venta = request.env['sale.order'].sudo().create(venta_nueva)
                        nueva_venta.action_confirm()
                        self.create_message_log("ws016",as_token,post,'ACEPTADO','OC recibidas correctamente')
                        return mensaje_correcto
                    else:
                        self.create_message_log("ws016",as_token,post,'RECHAZADO','Ya existe el registro que pretende almacenar')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws016",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws016",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws016",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws023',], auth="public", type="json", method=['POST'], csrf=False)
    def WS023(self, **post):
        post = yaml.load(request.httprequest.data)
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            myapikey = request.httprequest.headers.get("Authorization")
            if not myapikey:
                self.create_message_log("ws023",as_token,post,'RECHAZADO','API KEY no existe')
                return mensaje_error
            user_id = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=myapikey)
            request.uid = user_id
            if user_id:
                res['token'] = as_token
                # post = post['params']
                uid = user_id
                # request.session.logout()
                estructura = self.get_file('ws023.json')
                # es_valido = True
                es_valido = self.validar_json(post, esquema=estructura)

                if es_valido:
                    vals_picking = {}
                    for linea in post['params']:
                        docdate = post['params']['DocDate'].replace("T"," ")
                        docdate = docdate.replace("Z","")
                        sp = request.env['stock.picking']
                        sp_search = sp.sudo().search([('as_ot_num', '=', post['params']['DocNum'])])
                        if not sp_search:
                            #se seleccionan las ubicaciones si no esxiste se crea y se retorna el ID
                            slo = self.as_get_id('stock.location',post['params']['WarehouseCodeOrigin'])
                            sld = self.as_get_id('stock.location',post['params']['WarehouseCodeDestination'])
                            picking_type_id = request.env['stock.picking.type'].sudo().search([('sequence_code', '=', 'INT_PP_SF')])
                            picking = request.env['stock.picking'].sudo().create({
                                    'location_id': slo,
                                    'date': docdate,
                                    'scheduled_date': docdate,
                                    'location_dest_id': sld,
                                    'as_ot_num': post['params']['DocNum'],
                                    'as_ot_sap': post['params']['DocNum'],
                                    'origin': post['params']['DocNum'],
                                    'picking_type_id': picking_type_id.id,
                                    "company_id": request.env.user.company_id.id,
                                    'immediate_transfer': False,
                                    'l10n_cl_draft_status': False,
                                    'state': 'assigned',
                                })
                                # move from shelf1
                            for move in post['params']['DatosProdOC']:
                                uom_id = self.as_get_uom_id('uom.uom',move)
                                if not uom_id:
                                    return {
                                        "Token": as_token,
                                        "RespCode": 0,
                                        "RespMessage": "Unidad de Medida no existe" 
                                    }
                                product_id = self.as_get_product_id(move,uom_id)
                                cantidad = 0.0
                                for move_line in move['Detalle']:
                                    cantidad+=move_line['Quantity']
                                move1 = request.env['stock.move'].sudo().create({
                                    'name': move['ItemDescription'],
                                    'location_id': slo,
                                    'location_dest_id': sld,
                                    'picking_id': picking.id,
                                    'product_id': product_id,
                                    'product_uom': uom_id,
                                    'product_uom_qty': move['Quantity'],
                                    # 'quantity_done': move['Quantity'],
                                    "company_id": request.env.user.company_id.id,
                                    'state': 'assigned',
                                })
                                # move1.move_line_ids.unlink()
                                for move_line in move['Detalle']:
                                    lot_id = self.as_get_lot_id('stock.production.lot',move_line,product_id)
                                    move_line1 =request.env['stock.move.line'].sudo().create({
                                        'picking_id': move1.picking_id.id,
                                        'move_id': move1.id,
                                        'product_id': product_id,
                                        # 'qty_done': move_line['Quantity'],
                                        'product_uom_id': uom_id,
                                        'location_id': move1.location_id.id,
                                        'location_dest_id': move1.location_dest_id.id,
                                        'lot_id': lot_id,
                                        "company_id": request.env.user.company_id.id,
                                        'state': 'assigned',
                                        'location_processed': False,
                                    })
                            picking.state="assigned"
                            # picking.action_confirm()
                            # picking.action_assign()
                            picking.scheduled_date= picking.date
                            self.create_message_log("ws023",as_token,post,'ACEPTADO','OT recibidas correctamente')
                            return mensaje_correcto
                        else:
                            self.create_message_log("ws023",as_token,post,'RECHAZADO','Ya existe el registro que pretende almacenar')
                            return mensaje_error                        
                else:
                    self.create_message_log("ws023",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws023",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws023",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws005',], auth="public", type="json", method=['POST'], csrf=False)
    def WS005(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        mode =  post['mode'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json_mode('WS005',mode)
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS005']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws005",as_token,info,'ACEPTADO','OT recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws005",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws005",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws005",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws005",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws005",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws005",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws004',], auth="public", type="json", method=['POST'], csrf=False)
    def WS004(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json('WS004')
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS004']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws004",as_token,info,'ACEPTADO','OC recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws004",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws004",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws004",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws004",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws004",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws004",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws006',], auth="public", type="json", method=['POST'], csrf=False)
    def WS006(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json('WS006')
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS006']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws006",as_token,info,'ACEPTADO','OC recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws006",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws006",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws006",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws006",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws006",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws006",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws099',], auth="public", type="json", method=['POST'], csrf=False)
    def WS099(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json('WS099')
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS099']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws099",as_token,info,'ACEPTADO','OC recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws099",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws099",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws099",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws099",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws099",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws099",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws018',], auth="public", type="json", method=['POST'], csrf=False)
    def WS018(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json('WS018')
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS018']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws018",as_token,info,'ACEPTADO','OC recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws018",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws018",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws018",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws018",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws018",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws018",as_token,post,'RECHAZADO',str(e))
            return mensaje_error

    @http.route(['/tpco/odoo/ws021',], auth="public", type="json", method=['POST'], csrf=False)
    def WS021(self, **post):
        post = yaml.load(request.httprequest.data)
        res_id =  post['res_id'] 
        res = {}
        as_token = uuid.uuid4().hex
        mensaje_error = {			
                        "Token": as_token,				
                        "RespCode":-1,
                        "RespMessage":"Error de conexión"
                    }
        mensaje_correcto = {		
                    "Token": as_token,					
                    "RespCode":0,				
                    "RespMessage":"OT recibidas correctamente"				
            }
        try:
            auth_id = self.as_get_auth()
            request.uid = request.env.user.id
            if auth_id:
                res['token'] = as_token
                es_valido = True

                if es_valido:
                    sp = request.env['stock.picking']
                    sp_search = sp.sudo().search([('name', '=', res_id)])
                    if sp_search:
                        if not sp_search.as_enviado_sap:
                            json_res = sp_search.as_assemble_picking_json('WS021')
                            if json_res != {}:
                                headerVal = {
                                    'Authorization': 'Bearer '+str(auth_id)
                                }
                                as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
                                as_url_def=as_url+address_api['WS021']
                                r = requests.post(as_url_def, json=json_res, headers=headerVal)
                                json_rest = json.loads(r.text)
                                status = ''
                                body = ''
                                info = json.loads(r.text)
                                if r.ok:
                                    self.create_message_log("ws021",as_token,info,'ACEPTADO','OC recibidas correctamente')
                                    return mensaje_correcto
                                else:
                                    self.create_message_log("ws021",as_token,info,'RECHAZADO','El JSON fue rechazado.')
                                    return mensaje_error
                        else:
                            self.create_message_log("ws021",as_token,post,'RECHAZADO','El documento ya fue enviado a SAP.')
                            return mensaje_error
                    else:
                        self.create_message_log("ws021",as_token,post,'RECHAZADO','El registro que desea enviar no existe.')
                        return mensaje_error                        
                else:
                    self.create_message_log("ws021",as_token,post,'RECHAZADO','Estructura del Json Invalida')
                    return mensaje_error
            else:
                self.create_message_log("ws021",as_token,post,'RECHAZADO','Autenticación fallida')
                return mensaje_error
        except Exception as e:
            self.create_message_log("ws021",as_token,post,'RECHAZADO',str(e))
            return mensaje_error


    def as_get_auth(self):
        token = ''
        as_url = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_url')
        as_url_def=as_url+'/api/Usuarios/Login'
        as_login = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_login')
        as_password = request.env['ir.config_parameter'].sudo().get_param('as_equimetal_webservice.as_password')
        requestBody = {
            'usuario': as_login,
            'password': as_password,
        }
        try:
            r = requests.post(as_url_def, json=requestBody, headers={})
            if r.ok:
                text = r.text
                info = json.loads(text)
                if info['token']:
                    token =  info['token']                    
                else:
                    token =  False
        except Exception as e:
            token =  False
        return token

    def as_get_id(self,model,value):
        rw = request.env[model].sudo().search([('name','=',value)])
        rw_id = 0
        if rw:
            rw_id = rw.id
        else:
            rw_new_id = request.env[model].sudo().create({"name": value,})
            rw_id = rw_new_id.id
        return rw_id

    def as_get_uom_id(self,model,value):
        rw = request.env[model].sudo().search([('name','=',value['MeasureUnit'])],limit=1)
        rw_id = False
        if rw:
            rw_id = rw.id
        return rw_id

    def as_get_lot_id(self,model,value,product_id):
        rw = request.env[model].sudo().search([('name','=',value['DistNumber']),('product_id','=',product_id)],limit=1)
        rw_id = 0
        if rw:
            rw_id = rw.id
        else:
            rw_new_id = request.env[model].sudo().create({
                "name": value['DistNumber'],
                "product_id": product_id,
                "company_id": request.env.user.company_id.id,
                "create_date": value['DateProduction'].replace("T"," ").replace("Z",""),
                "expiration_date": value['DateExpiration'].replace("T"," ").replace("Z",""),
                })
            rw_id = rw_new_id.id
        return rw_id
        
    def as_get_product_id(self,linea,uom_id):
        producto = request.env['product.template']
        producto_search = producto.sudo().search([('default_code', '=', linea['ItemCode'])])
        if producto_search.id:
            producto_id = producto_search.id
            product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
            product_product_id = product_product.id
        else:
            product_data = {
                "name": str(linea['ItemDescription']) or "",
                "type": "product",
                "categ_id": 1,
                "default_code": str(linea['ItemCode']) or "",
                "barcode": "",
                "list_price": 1,
                "standard_price": 0,
                "uom_id": uom_id,
                "uom_po_id": uom_id,
                "purchase_ok": True,
                "sale_ok": True,
                "tracking": 'lot',
                "company_id": request.env.user.company_id.id,
            }

            _logger.debug("\n\n\n\n\nproduct_data: %s", product_data)

            producto_nuevo = producto.sudo().create(product_data)
            producto_id = producto_nuevo.id
            product_product = request.env['product.product'].sudo().search([('product_tmpl_id', '=', producto_id)])[0]
            product_product_id = product_product.id
        return product_product_id

    def validar_json(self, el_json, esquema):
        try:
            validate(instance=el_json, schema=esquema)
        except jsonschema.exceptions.ValidationError as err:
            return False
        return True
    
    def create_message_log(self,method,token,json,state,as_motivo):
        val_message = {
            "name": method,
            "as_token": token,
            "as_fecha": datetime.now(),
            "as_json": json,
            "state": state,
            "as_motivo": as_motivo,
        }
        request.env['as.webservice.logs'].sudo().create(val_message)
    
    def get_file(self,file):
        text = ''
        json_dict = {}
        filepath = os.path.dirname(os.path.realpath(__file__)).split('controllers')[0]+'static/src/'+file
        with open(filepath, 'rb') as outfile:
            text = outfile.read()
        json_dict = json.loads(text)
        return json_dict

    def as_convert(txt,digits=50,is_number=False):
        if is_number:
            num = re.sub("\D", "", txt)
            if num == '':
                return 0
            return int(num[0:digits])
        else:
            return txt[0:digits]           
        