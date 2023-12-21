prod = False

if prod:
    proxies = {}
    current_path = '/home/user/python/sale-parser-vishcopt/'
else:
    proxies = {'https': 'http://194.67.202.81:9138'}
    current_path = ''