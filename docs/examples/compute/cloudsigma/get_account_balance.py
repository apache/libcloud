from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls('username', 'password', region='zrh', api_version='2.0')

balance = driver.ex_get_balance()

values = {'balance': balance['balance'], 'currency': balance['currency']}
print('Account balance: %(balance)s %(currency)s' % values)
