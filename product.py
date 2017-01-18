#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import Workflow, ModelView, ModelSQL, ModelSingleton, fields
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

__all__ = ['CodigoBarras','ConfigurationBarcode']
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

_NOLISTAS = [
    ('no_1', '1 lista de precio'),
    ('no_2', '2 listas de precios'),
    ('no_3', '3 listas de precios'),
]


class ConfigurationBarcode(ModelSingleton, ModelSQL, ModelView):
    'Configuration Barcode'
    __name__ = 'product.configuration_barcode'

    lista_precio = fields.Many2One('product.price_list', 'Lista de precio 1', states={
        'required': Eval('no_lista_precio').in_(['no_1','no_2','no_3']),
    })

    etiqueta_1 = fields.Char('Etiqueta impresion', states={
        'required': Eval('no_lista_precio').in_(['no_1','no_2','no_3']),
    })

    lista_precio_oferta = fields.Many2One('product.price_list', 'Lista de precio 2', states={
        'invisible': Eval('no_lista_precio').in_(['no_1']),
        'required': Eval('no_lista_precio').in_(['no_2', 'no_3']),
    })

    etiqueta_2 = fields.Char('Etiqueta impresion', states={
        'invisible': Eval('no_lista_precio').in_(['no_1']),
        'required': Eval('no_lista_precio').in_(['no_2', 'no_3']),
        })

    lista_precio_credito = fields.Many2One('product.price_list', 'Lista de precio 3', states={
        'invisible': Eval('no_lista_precio').in_(['no_1', 'no_2']),
        'required': Eval('no_lista_precio').in_(['no_3']),
    })
    etiqueta_3 = fields.Char('Etiqueta impresion', states={
        'invisible': Eval('no_lista_precio').in_(['no_1', 'no_2']),
        'required': Eval('no_lista_precio').in_(['no_3']),
        })

    formato = fields.Selection(_FORMATO, 'Formato')
    no_lista_precio = fields.Selection(_NOLISTAS, 'No. de Listas', help="Numero de listas de precios que se imprimira en la etiqueta")


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
        numero = 0
        etiqueta = ""
        etiqueta_2 = ""
        etiqueta_3 = ""

        for c in configuration:
            if c.no_lista_precio == 'no_1':
                lista_normal = c.lista_precio
                numero = 1
                etiqueta = c.etiqueta_1

            if c.no_lista_precio == 'no_2':
                lista_normal = c.lista_precio
                lista_oferta = c.lista_precio_oferta
                numero = 2
                etiqueta = c.etiqueta_1
                etiqueta_2 = c.etiqueta_2

            if c.no_lista_precio == 'no_3':
                lista_normal = c.lista_precio
                lista_oferta = c.lista_precio_oferta
                lista_credito = c.lista_precio_credito
                numero = 3
                etiqueta = c.etiqueta_1
                etiqueta_2 = c.etiqueta_2
                etiqueta_3 = c.etiqueta_3

        company = Company(company_id)
        precio = Decimal(0.0)
        precio_final = Decimal(0.0)
        precio_final_oferta = Decimal(0.0)
        precio_final_credito = Decimal(0.0)
        iva = Decimal(0.0)
        percentage = Decimal(0.0)

        Product = pool.get('product.template')
        product = records[0]
        tam = len(product.name)
        if tam > 70:
            name = str(product.name)[0:70]
        else:
            name = product.name

        Variante = pool.get('product.product')
        variantes = Variante.search([('template', '=', product)])
        code = ""
        cont = 1
        for v in variantes:
            code = v.code
            if cont == 1:
                code_eti = v.code

            if cont == 2:
                code = v.code
                break
            cont += 1


        for lista in product.listas_precios:
            if numero == 1:
                if lista.lista_precio == lista_normal:
                    precio_final = lista.fijo_con_iva
            if numero == 2:
                if lista.lista_precio == lista_normal:
                    precio_final = lista.fijo_con_iva
                elif lista.lista_precio == lista_oferta:
                    precio_final_oferta = lista.fijo_con_iva
            if numero == 3:
                if lista.lista_precio == lista_normal:
                    precio_final = lista.fijo_con_iva
                elif lista.lista_precio == lista_oferta:
                    precio_final_oferta = lista.fijo_con_iva
                elif lista.lista_precio == lista_credito:
                    precio_final_credito = lista.fijo_con_iva

        """
        level, path = tempfile.mkstemp(prefix='%s-%s-' % ('CODE 39', code))
        from cStringIO import StringIO as StringIO
        fp = StringIO()
        a = generate('code39', code, writer=ImageWriter(), output=fp)
        image = buffer(fp.getvalue())
        fp.close()
        """
        ref = None
        localcontext['company'] = company
        #localcontext['barcode1'] = image
        #localcontext['barcode2'] = image
        #localcontext['barcode3'] = image
        localcontext['name'] = name
        localcontext['precio'] = precio_final
        localcontext['precio_oferta'] = precio_final_oferta
        localcontext['precio_credito'] = precio_final_credito
        localcontext['etiqueta'] = etiqueta
        localcontext['etiqueta_2'] = etiqueta_2
        localcontext['etiqueta_3'] = etiqueta_3
        localcontext['numero'] = numero
        localcontext['code'] = code_eti
        localcontext['ref_pro'] = ref
        return super(CodigoBarras, cls).parse(report, records, data, localcontext)
