#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pyson import Id
from trytond.report import Report
from trytond.transaction import Transaction
from trytond.modules.company import CompanyReport
from trytond.pool import Pool
from decimal import Decimal
from barcode import generate
import tempfile
from barcode.writer import ImageWriter

__all__ = ['Template', 'CodigoBarras','ConfigurationBarcode']
__metaclass__ = PoolMeta

_FORMATO = [
    ('tam_1', 'ETIQUETAS DE 3.8 cm X 2.5 cm'),
    ('tam_2', 'ETIQUETAS DE 5.1 cm X 2.5 cm'),
    ('tam_3', 'ETIQUETAS DE 5.7 cm X 2.7 cm'),
    ('tam_4', 'ETIQUETAS DE 7.6 cm X 2.5 cm'),
    ('tam_5', 'ETIQUETAS DE 8.0 cm X 4.0 cm'),
    ('tam_6', 'ETIQUETAS DE 10.2 cm X 7.6 cm'),
    ('tam_7', 'ETIQUETAS DE 10.2 cm X 10.2 cm'),
]

class Template:
    __name__ = 'product.template'

    variante = fields.Many2One('product.product', 'Codigo de producto', domain=[('template', '=', Eval('id'))])
    lista_precio = fields.Many2One('product.price_list', 'Lista de precio normal')
    lista_precio_oferta = fields.Many2One('product.price_list', 'Lista de precio oferta')
    purchase = fields.Many2One('purchase.purchase', 'Factura de proveedor', domain=[('lines.product', '=', Eval('variante'))])

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__
        cls._buttons.update({
            'actualizar': {
                'readonly': ~Eval('active', True),
            }
        })

    @fields.depends('variante', 'purchase')
    def on_change_variante(self):
        pool = Pool()
        res= {}
        if self.variante:
            PurchaseLine = pool.get('purchase.line')
            Purchase = pool.get('purchase.purchase')
            lines = PurchaseLine.search([('product', '=', self.variante.id)])
            for l in lines:
                line = l
            purchases = Purchase.search([('id', '=', line.purchase.id)])
            for p in purchases:
                purchase = p
            res['purchase'] = purchase.id
        return res

    @classmethod
    @ModelView.button
    def actualizar(cls, products):
        pool = Pool()
        PurchaseLine = pool.get('purchase.line')
        Purchase = pool.get('purchase.purchase')
        for product in products:
            if product.variante:
                lines = PurchaseLine.search([('product', '=', product.variante)])
            if lines:
                for l in lines:
                    line = l
                purchases = Purchase.search([('id', '=', line.purchase.id)])
                if purchases:
                    for p in purchases:
                        purchase = p
                    cls.write(products, {'purchase': purchase.id})

class ConfigurationBarcode(ModelSQL, ModelView):
    'Configuration Barcode'
    __name__ = 'product.configuration_barcode'

    lista_precio = fields.Many2One('product.price_list', 'Lista de precio normal')
    lista_precio_oferta = fields.Many2One('product.price_list', 'Lista de precio oferta')
    formato = fields.Selection(_FORMATO, 'Formato')

class CodigoBarras(Report):
    'Codigo Barras'
    __name__ = 'product.barras_report'

    @classmethod
    def parse(cls, report, records, data, localcontext=None):
        pool = Pool()
        Company = pool.get('company.company')
        company_id = Transaction().context.get('company')
        Taxes1 = pool.get('product.category-customer-account.tax')
        Taxes2 = pool.get('product.template-customer-account.tax')
        Configuration = pool.get('product.configuration_barcode')
        configuration = Configuration.search([('id', '=', 1)])
        for c in configuration:
            lista_normal = c.lista_precio
            lista_oferta = c.lista_precio_oferta

        company = Company(company_id)
        precio = Decimal(0.0)
        precio_final = Decimal(0.0)
        precio_final_oferta = Decimal(0.0)
        iva = Decimal(0.0)
        percentage = Decimal(0.0)

        Product = pool.get('product.template')
        product = records[0]

        for lista in product.listas_precios:
            if lista.lista_precio == lista_normal:
                precio_final = lista.fijo
            elif lista.lista_precio == lista_oferta:
                precio_final_oferta = lista.fijo

        level, path = tempfile.mkstemp(prefix='%s-%s-' % ('CODE 39', product.variante.code))
        from cStringIO import StringIO as StringIO
        fp = StringIO()
        a = generate('code39', product.variante.code, writer=ImageWriter(), output=fp)
        image = buffer(fp.getvalue())
        fp.close()
        ref = None

        localcontext['company'] = company
        localcontext['barcode2'] = image
        localcontext['precio']=precio_final
        localcontext['precio_oferta']=precio_final_oferta
        localcontext['ref_pro']=ref
        return super(CodigoBarras, cls).parse(report, records, data, localcontext)
