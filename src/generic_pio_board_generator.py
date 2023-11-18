#!/usr/bin/python
# -*- coding: UTF-8 -*-

import csv
import os
import re
from collections import defaultdict
from string import Template

rows = defaultdict(list)
dirname = os.path.dirname(__file__)

bspDict = {
    'AT32F402_405': ['AT32F402', 'AT32F405'],
    'AT32F403': ['AT32F403'],
    'AT32F403A_407': ['AT32F403A', 'AT32F407'],
    'AT32F413': ['AT32F413'],
    'AT32F415': ['AT32F415'],
    'AT32F421': ['AT32F421'],
    'AT32F423': ['AT32F423'],
    'AT32F425': ['AT32F425'],
    'AT32F435_437': ['AT32F435', 'AT32F437'],
    'AT32WB415': ['AT32WB415']
}


def get_ocd_target(product, sku):
    if(product in ['AT32F435', 'AT32F437']):
        return product.lower() + 'xM' if sku[9] == 'M' else product.lower() + 'xx'
    else:
        return product.lower() + 'xx'


def get_bsp(product):
    for item in bspDict:
        if product in bspDict[item]:
            return item


with open(os.path.join(dirname, 'board.tpl.json'), "r") as template_file:
    template = Template(template_file.read())

with open(os.path.join(dirname, 'at32.csv')) as f:
    reader = csv.DictReader(f, delimiter=',')
    for item in reader:
        # when SRAM is by '96/224' format, means ram can be configured to 96K or 224K,
        # when SRAM is by '96+6' format, means ram can be configured to 96K or 102K,
        # we need to list all possible ram size for sram_options,
        # and use the max size for sram_size


        sram_sizes = item['SRAM'].split('/')
        possible_sram_sizes = []
        sram_options = []
        for size in sram_sizes:
            if '+' in size:
                min_size, extra_size = size.split('+')
                sram_options.append(min_size + 'K')
                sram_options.append(str(int(min_size) + int(extra_size)) + 'K')

                possible_sram_sizes.append(min_size)
                possible_sram_sizes.append(str(int(min_size) + int(extra_size)))
            else:
                sram_options.append(size + 'K')
                possible_sram_sizes.append(size)
        item['sram_options'] = '/'.join(sram_options)
        item['sram_size'] = max([int(size) for size in possible_sram_sizes]) * 1024
        

        item['SKU'] = item['SKU']
        item['variant'] = item['SKU'].replace('-','_')
        item['f_cpu'] = int(item['Speed']) * 1000000
        item['flash_size'] = int(item['Flash'])*1024
        item['ocd_target'] = get_ocd_target(item['Product'], item["SKU"])
        item['product_flash_series'] = item['Product'] + \
            'x' + item['SKU'].replace(item['Product'], '')[1]
        item['bsp'] = get_bsp(item['Product'])
        rows[item['SKU']] = item

for item in rows:
    # print(rows[item])
    # print(template.substitute(rows[item]))
    with open(os.path.join(dirname, '../boards/generic{}.json'.format(item)), 'w') as out:
        out.write(template.substitute(rows[item]))
