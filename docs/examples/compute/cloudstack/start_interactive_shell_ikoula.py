import os

from IPython.terminal.embed import InteractiveShellEmbed

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = os.getenv('IKOULA_API_KEY')
secretkey = os.getenv('IKOULA_SECRET_KEY')

Driver = get_driver(Provider.IKOULA)

conn = Driver(key=apikey, secret=secretkey)

shell = InteractiveShellEmbed(banner1='Hello from Libcloud Shell !!')
shell()
