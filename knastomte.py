#!/usr/bin/env python3

import argparse
import csv
from datetime import datetime
import dateutil.parser
from glob import glob
import os
from time import time
import xml.etree.ElementTree as ET


columns = [ 'allocation', 'invoice_index', 'invoice_no', 'invoice_date', 'pay_date', 'customer_number', 'customer_name',
            'tax_total', 'tax_total_s', 'invoice_total', 'invoice_total_s', 'allocation_code',
            'allocation_lookup', 'gl_code_name',
          ]


def add_col(table, inp_col, new_col, func):
    global columns
    columns += [new_col]
    for row in table:
        i = columns.index(inp_col)
        val = row[i]
        row += [func(val)]


def timestamp2day():
    return datetime.fromtimestamp(time()).isoformat().partition('T')[0]


def list_files(wildcard):
    return [(fn,fn) for fn in glob(wildcard)]


def open_outp(fn):
    return open(fn, 'w', newline='')


def move_files(today, files):
    try:
        os.mkdir(today)
    except:
        pass
    for fname,fobj in files:
        tgt_fname = os.path.basename(fname)
        os.rename(fname, today+'/'+tgt_fname)


def main(options):
    # load table
    allocation_lookup = eval(open('allocation.cfg').read())

    invoice_index = 1
    table = []
    files = list_files(options.input_wildcard)
    for fname,fobj in files:
        print('processing %s...' % fname)
        # load import file and place each row in table
        ns = dict([node for _,node in ET.iterparse(fobj, events=['start-ns'])])
        ns['ns'] = ns['']
        if hasattr(fobj, 'seek'):
            fobj.seek(0)
        e = ET.parse(fobj).getroot()
        for account in e.findall('ns:account', ns):
            customer_id = account.find('ns:cust_id', ns).text
            customer_name = account.find('ns:cust_name', ns).text
            for invoice in account.findall('ns:invoice', ns):
                invoice_date = invoice.find('ns:invoice_date', ns).text
                timestamp = dateutil.parser.parse(invoice_date).timestamp()
                invoice_date = datetime.fromtimestamp(timestamp).isoformat().partition('T')[0]
                payment_date = invoice.find('ns:payment_due_date', ns).text
                timestamp = dateutil.parser.parse(payment_date).timestamp()
                payment_date = datetime.fromtimestamp(timestamp).isoformat().partition('T')[0]
                # tax_total = invoice.find('ns:total_tax_value', ns).text
                # tax_total = float(tax_total)
                # tax_total_s = ('%.2f'%float(tax_total)).replace('.',',')
                # invoice_total = invoice.find('ns:invoice_total', ns).text
                # invoice_gross = float(invoice_total)
                # invoice_total = invoice_gross + tax_total
                # invoice_total_s = ('%.2f'%invoice_total).replace('.',',')
                invoice_number = invoice.find('ns:invoice_number', ns).text
                allocs = []
                for invoice_item in invoice.findall('ns:invoice_item', ns):
                    tax_total = invoice_item.find('ns:total_tax_amount', ns).text
                    tax_total = float(tax_total)
                    tax_total_s = '?'
                    invoice_gross = invoice_item.find('ns:gross_amount', ns).text
                    invoice_gross = float(invoice_gross)
                    invoice_net = invoice_gross - tax_total
                    print(invoice_gross, invoice_net, tax_total)
                    invoice_total_s = '?'

                    allocation = invoice_item.find('ns:allocation_code_name', ns).text
                    gl_code_name = invoice_item.find('ns:gl_code_name', ns).text.split()[0]
                    # if allocation not in allocation_lookup:
                        # print('FATAL: no such allocation %s in allocation.cfg' % allocation)
                        # return
                    # allocation_code = allocation_lookup[allocation]
                    table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, customer_name, tax_total, tax_total_s, -invoice_gross, invoice_total_s, 'debit',  allocation_lookup['Debiteuren'], gl_code_name]]
                    table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, customer_name, tax_total, tax_total_s,   +invoice_net, invoice_total_s, 'credit', allocation_lookup['fldDagboek'], gl_code_name]]
                    table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, customer_name, tax_total, tax_total_s,     +tax_total, invoice_total_s, 'tax',    allocation_lookup['BTW'], gl_code_name]]
                invoice_index += 1

    add_col(table, 'allocation_lookup', 'fldDagboek', lambda s: s)
    add_col(table, 'invoice_index',     'fldBoekingcode', lambda s: s)
    add_col(table, 'invoice_date',      'fldDatum', lambda s: '-'.join(reversed(s.split('-'))))
    add_col(table, 'gl_code_name',      'fldGrootboeknummer', lambda x: x)
    add_col(table, 'invoice_total',     'fldDebet', lambda x: ('%.2f'%round(-x,2) if x<0 else '0.00'))
    add_col(table, 'invoice_total',     'fldCredit', lambda x: ('%.2f'%round(x,2) if x>0 else '0.00'))
    add_col(table, 'customer_name',     'fldOmschrijving', lambda s: s)
    # append ' $invoice_no' to customer names
    for row in table:
        i = columns.index('invoice_no')
        row[-1] += ' - ' + str(row[i])
    add_col(table, 'customer_number',   'fldRelatiecode', lambda s: s)
    add_col(table, 'invoice_no',        'fldFactuurnummer', lambda s: s)
    cols = ['fldDagboek', 'fldBoekingcode', 'fldDatum', 'fldGrootboeknummer', 'fldDebet', 'fldCredit', 'fldOmschrijving', 'fldRelatiecode', 'fldFactuurnummer']

    with open_outp(options.output_file) as wf:
        wr = csv.writer(wf)
        wr.writerow(cols)
        t = [[row[columns.index(c)] for row in table] for c in cols]
        for row in zip(*t):
            wr.writerow(row)

    # show we did something
    gross_total = sum(float(row[columns.index('fldDebet')])+float(row[columns.index('fldCredit')]) for row in table if row[columns.index('allocation_code')]=='debit')
    net_total = sum(float(row[columns.index('fldDebet')])+float(row[columns.index('fldCredit')]) for row in table if row[columns.index('allocation_code')]=='credit')
    print('Converted %i invoices. Gross %.2f EUR = net %.2f EUR. Written to "%s".' % (len(table)//3, gross_total, net_total, options.output_file))

    move_files(options.today, files)



if __name__ == '__main__':
    print('knastomte v0.2')
    parser = argparse.ArgumentParser()
    today = timestamp2day()
    parser.add_argument('-i', '--input-wildcard', default='input/*.xml', help='invoice XML files to process')
    parser.add_argument('-o', '--output-file', default='verkoopfactuur-import-'+today+'.csv', help='output Excel file for import into SnelStart')
    options = parser.parse_args()
    options.today = today
    main(options)
    input('Press enter. ')
