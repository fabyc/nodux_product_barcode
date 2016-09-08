#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields, ModelView
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

__all__ = ['Template', 'CodigoBarras']
__metaclass__ = PoolMeta

class Template:
    __name__ = 'product.template'

    variante = fields.Many2One('product.product', 'Codigo de producto', domain=[('template', '=', Eval('id'))])
    lista_precio = fields.Many2One('product.price_list', 'Lista de precio')
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
        company = Company(company_id)
        precio = Decimal(0.0)
        iva = Decimal(0.0)
        percentage = Decimal(0.0)

        Product = pool.get('product.template')
        product = records[0]
        precio_final = product.list_price
        if  product.lista_precio:
            precio = product.list_price

            if product.taxes_category == True:
                if product.category.taxes_parent == True:
                    taxes1= Taxes1.search([('category','=', product.category.parent)])
                    taxes2 = Taxes2.search([('product','=', product)])
                else:
                    taxes1= Taxes1.search([('category','=', product.category)])
                    taxes2 = Taxes2.search([('product','=', product)])
            else:
                taxes1= Taxes1.search([('category','=', product.category)])
                taxes2 = Taxes2.search([('product','=', product)])

            if taxes1:
                for t in taxes1:
                    iva = precio * t.tax.rate
            elif taxes2:
                for t in taxes2:
                    iva = precio * t.tax.rate
            elif taxes3:
                for t in taxes3:
                    iva = precio * t.tax.rate
            precio_total = precio + iva

            lista_precios = product.lista_precio
            if lista_precios.lines:
                for line in lista_precios.lines:
                    if line.percentage > 0:
                        percentage = line.percentage/100
            precio_final = precio_total * (1- percentage)
            if company.currency:
                precio_final = company.currency.round(precio_final)
        level, path = tempfile.mkstemp(prefix='%s-%s-' % ('CODE 39', product.variante.code))
        from cStringIO import StringIO as StringIO
        fp = StringIO()
        a = generate('code39', product.variante.code, writer=ImageWriter(), output=fp)
        image = buffer(fp.getvalue())
        fp.close()
        ref = None
        if product.purchase:
            if product.purchase.supplier_reference:
                cont = 0
                references = product.purchase.supplier_reference.split('-')
                for r in references:
                    reference = r
                len_r = len(reference)
                for l in reference:
                    if l == '0':
                        cont = cont +1
                    elif l != '0':
                        break

                ref = reference[cont:len_r]

        localcontext['company'] = company
        localcontext['barcode2'] = image
        localcontext['precio']=precio_final
        localcontext['ref_pro']=ref
        return super(CodigoBarras, cls).parse(report, records, data, localcontext)
