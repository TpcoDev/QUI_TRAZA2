# -*- coding: utf-8 -*-
{
    'name': "Stock Barcode Quimetal",
    'summary': "Use barcode scanners to process logistics operations",

    'description': """
        
    """,
    'author': "TPCO",
    'website': "http://www.tpco.com",
    'category': 'Inventory/Inventory',
    'version': '1.0',
    'depends': ['stock_barcode', 'as_stock_equimetal'],

    # always loaded
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/barcode_move_line_views.xml',
    ],

    'qweb': [
        "static/src/xml/qweb_templates.xml",
    ],
}
