import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PROFIT_BRICKS)

# Get ProfitBricks credentials from environment variables
pb_username = os.environ.get("PROFITBRICKS_USERNAME")
pb_password = os.environ.get("PROFITBRICKS_PASSWORD")

driver = cls(pb_username, pb_password)

datacenters = driver.list_datacenters()
# Looks for existing data centers named 'demo-dc'
datacenter = [dc for dc in datacenters if dc.name == "demo-dc"][0]

# Create a public LAN
lan = driver.ex_create_lan(datacenter, is_public=True)
print(lan)
