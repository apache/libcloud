from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Driver = get_driver(Provider.IBM)
conn = Driver("user@name.com", "ibm_sce_password")

images = conn.list_images()
image = [i for i in images if i.id == "20014110"][0]

locations = conn.list_locations()
location = [loc for loc in locations if loc.id == "82"][0]

sizes = conn.list_sizes()
size = [s for s in sizes if s.id == "COP32.1/2048/60"][0]

node = conn.create_node(
    name="windows box",
    image=image,
    size=size,
    ex_configurationData={"UserName": "someone", "Password": "Wind0wsPass"},
    location=location,
)
print(conn.list_nodes())
