# -*- coding: utf-8 -*-
{
    'name' : "Ahorasoft EQUIMETAL stock  customizaciones",
    'version' : "1.1.7",
    'author'  : "Ahorasoft",
    'description': """
stock equimetal
===========================

Custom module for Latproject
    """,
    'category' : "Stock",
    'depends' : ["base","stock",'base_setup'],
    'website': 'http://www.ahorasoft.com',
    'data' : [
                'wizard/as_menu.xml',
                'views/as_campos_x.xml',
                'report/as_reportes_etiquetas_pdf.xml',
                'report/as_reporte_2.xml',
                'data/as_template_mail.xml',
                'views/as_format_report.xml',
                'views/as_stock_picking.xml',
                'views/as_res_config.xml',
                'views/as_stock_location.xml',
                'security/ir.model.access.csv',
             ],
    'demo' : [],
    'installable': True,
    'auto_install': False
}
