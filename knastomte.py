#!/usr/bin/env python3

import argparse
import csv
from datetime import datetime
import dateutil.parser
from glob import glob
import os
from time import time
import xml.etree.ElementTree as ET


columns = [ 'allocation', 'invoice_index', 'invoice_no', 'invoice_date', 'pay_date', 'customer_number',
            'tax_total', 'tax_total_s', 'invoice_total', 'invoice_total_s', 'allocation_code',
            'booking_no'
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


def main():
    print('knastomte v0.1')
    parser = argparse.ArgumentParser()
    today = timestamp2day()
    parser.add_argument('-i', '--input-wildcard', default='*.xml', help='invoice XML files to process')
    parser.add_argument('-o', '--output-file', default='verkoopfactuur-import-'+today+'.csv', help='output Excel file for import into SnelStart')
    options = parser.parse_args()

    # load table
    allocation_lookup = eval(open('allocation.cfg').read())

    invoice_index = 1
    table = []
    files = glob(options.input_wildcard)
    for fname in files:
        print('processing %s...' % fname)
        # load import file and place each row in table
        ns = dict([node for _,node in ET.iterparse(fname, events=['start-ns'])])
        ns['ns'] = ns['']
        e = ET.parse(fname).getroot()
        for account in e.findall('ns:account', ns):
            customer_id = account.find('ns:cust_id', ns).text
            for invoice in account.findall('ns:invoice', ns):
                invoice_date = invoice.find('ns:invoice_date', ns).text
                timestamp = dateutil.parser.parse(invoice_date).timestamp()
                invoice_date = datetime.fromtimestamp(timestamp).isoformat().partition('T')[0]
                payment_date = invoice.find('ns:payment_due_date', ns).text
                timestamp = dateutil.parser.parse(payment_date).timestamp()
                payment_date = datetime.fromtimestamp(timestamp).isoformat().partition('T')[0]
                tax_total = invoice.find('ns:total_tax_value', ns).text
                tax_total = float(tax_total)
                tax_total_s = ('%.2f'%float(tax_total)).replace('.',',')
                invoice_total = invoice.find('ns:invoice_total', ns).text
                invoice_gross = float(invoice_total)
                invoice_total = invoice_gross + tax_total
                invoice_total_s = ('%.2f'%invoice_total).replace('.',',')
                invoice_number = invoice.find('ns:invoice_number', ns).text
                allocs = []
                for invoice_item in invoice.findall('ns:invoice_item', ns):
                    allocation = invoice_item.find('ns:allocation_code_name', ns).text
                    if allocation not in allocation_lookup:
                        print('FATAL: no such allocation %s in allocation.cfg' % allocation)
                        return
                    allocation_code = allocation_lookup[allocation]
                    allocs += [(allocation_code,allocation)]
                allocation_code, allocation = sorted(allocs)[0]
                table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, tax_total, tax_total_s, -invoice_total, invoice_total_s, allocation_code, allocation_lookup['Debiteuren']]]
                table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, tax_total, tax_total_s, +invoice_gross, invoice_total_s, allocation_code, allocation_code]]
                table += [[allocation, invoice_index, invoice_number, invoice_date, payment_date, customer_id, tax_total, tax_total_s,     +tax_total, invoice_total_s, allocation_code, allocation_lookup['BTW']]]
                invoice_index += 1

    add_col(table, 'invoice_index',     'fldDagboek', lambda i: allocation_lookup['fldDagboek'])
    add_col(table, 'invoice_index',     'fldBoekingcode', lambda s: s)
    add_col(table, 'invoice_date',      'fldDatum', lambda s: '-'.join(reversed(s.split('-'))))
    add_col(table, 'booking_no',        'fldGrootboeknummer', lambda x: x)
    add_col(table, 'invoice_total',     'fldDebet', lambda x: round(-x if x<0 else 0, 2))
    add_col(table, 'invoice_total',     'fldCredit', lambda x: round(x if x>0 else 0, 2))
    add_col(table, 'allocation',        'fldOmschrijving', lambda s: s)
    add_col(table, 'customer_number',   'fldRelatiecode', lambda s: s)
    add_col(table, 'invoice_no',        'fldFactuurnummer', lambda s: s)
    cols = ['fldDagboek', 'fldBoekingcode', 'fldDatum', 'fldGrootboeknummer', 'fldDebet', 'fldCredit', 'fldOmschrijving', 'fldRelatiecode', 'fldFactuurnummer']

    with open(options.output_file, 'w', newline='') as wf:
        wr = csv.writer(wf)
        wr.writerow(cols)
        t = [[row[columns.index(c)] for row in table] for c in cols]
        for row in zip(*t):
            wr.writerow(row)

    # show we did something
    gross_total = sum(row[columns.index('fldDebet')]+row[columns.index('fldCredit')] for row in table if row[columns.index('booking_no')]==1300)
    net_total = sum(row[columns.index('fldDebet')]+row[columns.index('fldCredit')] for row in table if row[columns.index('booking_no')]==8200)
    print('Converted %i invoices. Gross %.2f EUR = net %.2f EUR. Written to "%s".' % (len(table)//3, gross_total, net_total, options.output_file))

    try:
        os.mkdir(today)
    except:
        pass
    for fname in files:
        os.rename(fname, today+'/'+fname)



if __name__ == '__main__':
    main()
    input('Press enter. ')
