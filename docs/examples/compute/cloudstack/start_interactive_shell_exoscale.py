import os

# pylint: disable=import-error
from IPython.terminal.embed import InteractiveShellEmbed

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = os.getenv("EXOSCALE_API_KEY")
secretkey = os.getenv("EXOSCALE_SECRET_KEY")

Driver = get_driver(Provider.EXOSCALE)

conn = Driver(key=apikey, secret=secretkey)

shell = InteractiveShellEmbed(banner1="Hello from Libcloud Shell !!")
shell()
