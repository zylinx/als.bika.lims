# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.browser.bika_listing import BikaListingView
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import currency_format
import csv
from cStringIO import StringIO


class InvoiceBatchInvoicesView(BikaListingView):
    def __init__(self, context, request):
        super(InvoiceBatchInvoicesView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.contentFilter = {}
        self.title = context.Title()
        self.description = ""
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_all_checkbox = False
        self.show_select_column = True
        self.pagesize = 50
        request.set('disable_border', 1)
        self.context_actions = {}
        self.columns = {
            'id': {'title': _('Invoice Number'),
                'toggle': True },
            'Created': {'title': _('Created'),
                'toggle': True },
            'client': {'title': _('Client'),
                'toggle': True},
            'email': {'title': _('Email Address'),
                'toggle': False},
            'phone': {'title': _('Phone'),
                'toggle': False},
            'invoicedate': {'title': _('Invoice Date'),
                'toggle': True},
            'startdate': {'title': _('Start Date'),
                'toggle': False},
            'enddate': {'title': _('End Date'),
                'toggle': False},
            'subtotal': {'title': _('Subtotal'),
                'toggle': False},
            'vatamount': {'title': _('VAT'),
                'toggle': False},
            'total': {'title': _('Total'),
                'toggle': True},
            }
        self.review_states = [
            {
                'id': 'default',
                'contentFilter': {},
                'title': _('Default'),
                'transitions': [],
                'columns': [
                    'id',
                    'Created',
                    'client',
                    'email',
                    'phone',
                    'invoicedate',
                    'startdate',
                    'enddate',
                    'subtotal',
                    'vatamount',
                    'total',
                ],
            },
        ]

    def getInvoices(self, contentFilter):
        return self.context.objectValues('Invoice')

    def folderitems(self, full_objects=False):
        currency = currency_format(self.context, 'en')
        self.show_all = True
        self.contentsMethod = self.getInvoices
        items = BikaListingView.folderitems(self, full_objects)
        for item in items:
            obj = item['obj']
            item['replace']['id'] = \
                "<a href='%s'>%s</a>" % (item['url'], obj.getId())

            client = obj.getClient()
            if client:
                item['client'] = client.Title()
                item['replace']['client'] = "<a href='%s'>%s</a>" % (
                    (client.absolute_url(), client.Title()))
                item['email'] = client.getEmailAddress()
                item['replace']['email'] = "<a href='%s'>%s</a>" % (
                    'mailto:%s' % client.getEmailAddress(),
                    client.getEmailAddress())
                item['phone'] = client.getPhone()
            else:
                item['client'] = ''
                item['email'] = ''
                item['phone'] = ''
            item['Created'] = self.ulocalized_time(obj.created())
            item['invoicedate'] = self.ulocalized_time(obj.getInvoiceDate())
            item['startdate'] = self.ulocalized_time(obj.getBatchStartDate())
            item['enddate'] = self.ulocalized_time(obj.getBatchEndDate())
            item['subtotal'] = currency(obj.getSubtotal())
            item['vatamount'] = currency(obj.getVATAmount())
            item['total'] = currency(obj.getTotal())
        return items


class BatchFolderExportCSV(InvoiceBatchInvoicesView):
    def __call__(self, REQUEST, RESPONSE):
        delimiter = ','
        filename = 'invoice_batch.txt'
        # Getting the invoice batch
        container = self.context
        assert container
        container.plone_log("Exporting InvoiceBatch to CSV format for PASTEL")
        # Getting the invoice batch's invoices
        invoices = self.getInvoices({})
        if not len(invoices):
            container.plone_log("InvoiceBatch contains no entries")

        rows = []
        _ordNum = ''
        for invoice in invoices:
            new_invoice = True
            _invNum     = "%s" % invoice.getId()
            _clientNum  = "%s" % invoice.getClient().getAccountNumber()
            _invDate    = "%s" % invoice.getInvoiceDate().strftime('%d/%m/%Y')
            _monthNum = invoice.getInvoiceDate().month()
            if _monthNum < 7:
                _periodNum = _monthNum + 6
            else:
                _periodNum = _monthNum - 6
            _periodNum  = "%s" % _monthNum

            _message1 = ''
            _message2 = ''
            _message3 = ''

            items = invoice.invoice_lineitems
            mixed = [(item.get('OrderNumber', ''), item) for item in items]
            mixed.sort()
            lines = [t[1] for t in mixed]

            #iterate through each invoice line
            for line in lines:
                if new_invoice or line.get('OrderNumber', '') != _ordNum:
                    new_invoice = False
                    _ordNum  = line.get('OrderNumber', '')

                    #create header csv entry as a list
                    header = [ \
                        "Header", _invNum, " ", " ", _clientNum, _periodNum, \
                        _invDate, _ordNum, "N", 0, _message1,  _message2, \
                        _message3, "", "", "", "", "", "", 0, "", "", "", "", \
                        0, "", "", "N"]
                    rows.append(header)

                _quant = 1
                _unitp = format(line.get('Subtotal'),'.2f')
                _inclp = format(line.get('Total'),'.2f')
                _item = line.get('ItemDescription', '')
                _desc  = "Analysis: %s" %_item[:40]
                if _item.startswith('Water') or _item.startswith('water'):
                    _icode = "2"
                else:
                    _icode = "1"
                _ltype = "4"
                _ccode = ""

                #create detail csv entry as a list
                detail = ["Detail", 0, _quant, _unitp, _inclp,\
                          "", "1", "0", "0", _icode, _desc,\
                          _ltype, _ccode, ""]
                rows.append(detail)

        #convert lists to csv string
        ramdisk = StringIO()
        writer = csv.writer(ramdisk, delimiter=delimiter)
        assert(writer)
        writer.writerows(rows)
        result = ramdisk.getvalue()
        ramdisk.close()
        #stream file to browser
        setheader = RESPONSE.setHeader
        setheader('Content-Length', len(result))
        setheader('Content-Type',
                  'text/x-comma-separated-values')
        setheader('Content-Disposition', 'inline; filename=%s' % filename)
        RESPONSE.write(result)
