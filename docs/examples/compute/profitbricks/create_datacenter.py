import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PROFIT_BRICKS)

# Get ProfitBricks credentials from environment variables
pb_username = os.environ.get("PROFITBRICKS_USERNAME")
pb_password = os.environ.get("PROFITBRICKS_PASSWORD")

driver = cls(pb_username, pb_password)

# list available locations
locations = driver.list_locations()

my_location = None
# US Las Vegas location
for loc in locations:
    if loc.id == "us/las":
        my_location = loc
        break

# Create a data center
datacenter = driver.ex_create_datacenter("demo-dc", my_location)
print(datacenter)
