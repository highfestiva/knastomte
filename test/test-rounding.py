#!/usr/bin/env python3

from collections import namedtuple
import io
import knastomte

xml = \
'''<invoice_batch_generic xmlns="http://tempuri.org/invoice_batch_generic.xsd">
	<account>
		<cust_id>500081</cust_id>
		<cust_name>RVS Afvoergoten BV</cust_name>
		<invoice>
			<invoice_date>2020-10-05T00:00:00-04:00</invoice_date>
			<invoice_number>205028</invoice_number>
			<invoice_total>%s</invoice_total>
			<total_tax_value>%s</total_tax_value>
			<payment_due_date>2020-11-04T00:00:00-05:00</payment_due_date>
			<invoice_item>
				<allocation_code_name>Discount</allocation_code_name>
			</invoice_item>
		</invoice>
	</account>
</invoice_batch_generic>
'''

outf = None

def list_files(wildcard):
    return [('xml', io.StringIO(xml2))]

def open_outp(fn):
    global outf
    outf = io.StringIO()
    outf.close = lambda: None
    return outf

knastomte.list_files = list_files
knastomte.open_outp = open_outp
knastomte.move_files = lambda x,y: None

import xml.etree.ElementTree as ET

Opts = namedtuple('Options', ['input_wildcard', 'output_file', 'today'])
for a in range(-40, 50, 10):
    for b in range(-9, 9+1):
        for c in range(-9, 9+1):
            net = (('%i'%a) + '.00' + ('%i'%b)) if b>=0 else (('%i'%(a-1)) + '.99' + ('%i'%(-b)))
            tax = (('%i'%(a//10)) + '.00' + ('%i'%c)) if c>=0 else (('%i'%((a-1)//10)) + '.99' + ('%i'%(-c)))
            print('net=%s, tax=%s' % (net, tax))
            xml2 = xml % (net, tax)
            knastomte.main(Opts('*', '?', None))
            results = [(cells[4],cells[5]) for line in outf.getvalue().splitlines() for cells in [line.split(',')]][1:]
            k_gross,k_net,k_tax = [(a if abs(float(a))>0 else b) for a,b in results]
            gross = float(net) + float(tax)
            print(gross, k_gross, net, k_net, tax, k_tax)
            assert round(abs(gross),2) == float(k_gross)
            assert round(abs(float(net)),2) == float(k_net)
            assert round(abs(float(tax)),2) == float(k_tax)
print('All tests ok!')
