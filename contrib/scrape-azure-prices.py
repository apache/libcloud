import json
import requests


PRICES_URL = "https://azure.microsoft.com/api/v3/pricing/virtual-machines/calculator/"


def get_azure_prices():
    prices_raw = requests.get(PRICES_URL).json()
    regions = []
    for region in prices_raw['regions']:
        regions.append(region['slug'])
    
    result = {"windows": {}, "linux": {}}
    parsed_sizes = {"lowpriority", "basic", "standard"}

    for offer, value in prices_raw['offers'].items():
        size_raw = offer.split("-")
        #  Servers that go by the core with global price are not yet added
        if len(size_raw) != 3 or size_raw[2] not in parsed_sizes:
            continue
        size = size_raw[2][0].upper() + size_raw[2][1:] + "_" +\
            size_raw[1][0].upper() + size_raw[1][1:]
        prices = {}
        if not value['prices'].get('perhour'):
            continue
        for region, price in value['prices']['perhour'].items():
            prices[region] = price['value']
        
        result[size_raw[0]] = {size:prices}
    return result
if __name__=="__main__":
    res = get_azure_prices()
    import pdb;pdb.set_trace()
    print("Yo")