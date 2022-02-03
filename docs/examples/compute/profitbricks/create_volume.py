import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PROFIT_BRICKS)

# Get ProfitBricks credentials from environment variables
pb_username = os.environ.get("PROFITBRICKS_USERNAME")
pb_password = os.environ.get("PROFITBRICKS_PASSWORD")

driver = cls(pb_username, pb_password)

datacenters = driver.ex_list_datacenters()
location = driver.ex_describe_location(ex_location_id="us/las")
datacenter = [dc for dc in datacenters if dc.extra["location"] == location.id]

images = driver.list_images(image_type="HDD")
image = [img for img in images if img.extra["location"] == location.id][0]
# Create a new SSD volume. Set `ex_type='HDD'` to create a HDD volume.
ssd_volume = driver.create_volume(
    name="Example SSD volume",
    size=100,
    image=image,
    ex_type="SSD",
    ex_datacenter=datacenter[0],
    ex_password="PuTSoMeSTRONGPaSsWoRdHeRe2017",
)
print(ssd_volume)
