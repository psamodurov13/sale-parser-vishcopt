import pandas as pd
import json
from rich.progress import track
from constants import *


def convert():
    with open(f'{current_path}products.json', 'r') as file:
        products = json.load(file)
    sn = ['Products',
     'AdditionalImages',
     'Specials',
     'Discounts',
     'Rewards',
     'ProductOptions',
     'ProductOptionValues',
     'ProductAttributes',
     'ProductFilters']


    prods_all = pd.read_excel(f'{current_path}products.xlsx', sn)
    prods = prods_all['Products'][['product_id', 'mpn']]
    exceptions = []
    for i in products:
        try:
            products[i].append(prods[prods['mpn'] == i].values[0][0])
        except Exception:
            products[i].append('0')
            exceptions.append(i)

    # Создаем DataFrame и приводим цены к розничным значениям
    data = pd.DataFrame.from_dict(products, orient='index', columns=['price', 'old', 'url', 'product_id'])
    data['price'] = data['price'].apply(lambda x: x.replace(' ', ''))
    data['old'] = data['old'].apply(lambda x: x.replace(' ', ''))
    data['price'] = data['price'].astype('float').round()
    data['old'] = data['old'].astype('float').round()
    data = data.loc[data['product_id'] != '0']
    data.loc[:, 'price'] *= 2
    data.loc[:, 'old'] *= 2
    data.loc[(data.price < 2500), 'price'] = data.price + 200

    # Генерируем XML файл
    if prod:
        path_to_data = '/home/user/web/sweethomedress.ru/public_html/data.xml'
    else:
        path_to_data = 'data.xml'
    with open(path_to_data, 'w') as file:
        file.write(data.to_xml())
        print('XML - создан')

    # Указываем новые акционныю цены в XLSX выгрузке
    data_specials = data[['product_id', 'price']]
    data_specials.insert(1, 'customer_group', 'Default')
    data_specials.insert(2, 'priority', '1')
    data_specials.insert(4, 'date_start', '0000-00-00')
    data_specials.insert(5, 'date_end', '2050-01-01')
    prods_all['Specials'] = pd.concat([prods_all['Specials'], data_specials])

    writer = pd.ExcelWriter(f'{current_path}products.xlsx', engine='xlsxwriter')

    for sheet_name in track(prods_all.keys(), description='[red]Закрузка в файл', style='red'):
        prods_all[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

    writer.save()
    print('XLSX - создан')
    print('Exceptions - ', exceptions)
