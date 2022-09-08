from pprint import pprint

import libcloud.security
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Get nttcis driver
libcloud.security.VERIFY_SSL_CERT = True
cls = get_driver(Provider.NTTCIS)
driver = cls("myusername", "mypassword", region="eu")

# Get location
location = driver.ex_get_location_by_id(id="EU7")

# Get network domain by location
networkDomainName = "Test Apache Libcloud"
network_domains = driver.ex_list_network_domains(location=location)
my_network_domain = [d for d in network_domains if d.name == networkDomainName][0]

vlan = driver.ex_list_vlans(name="Libcloud Test VLAN")[0]

# Get Image
images = driver.ex_list_customer_images(location=location)
image = images[1]

tags = driver.ex_list_tags()
pprint(tags)

ex_tagname_value_pairs = {}
ex_tagname_value_pairs["AA_Tag1"] = "demo 1"
ex_tagname_value_pairs["AA_Tag2"] = "demo 2"

ex_tagid_value_pairs = {}
ex_tagid_value_pairs["4927c8fd-7f41-4206-a7d5-c5def927c6d2"] = "demo 1"
ex_tagid_value_pairs["2579fc7c-a89c-47cd-ac3b-67999dded93b"] = "demo 2"


# Create node using vlan instead of private IPv4
node = driver.ex_create_node_uncustomized(
    name="test_server_05",
    image=image,
    ex_network_domain=my_network_domain,
    ex_is_started=False,
    ex_description=None,
    ex_cluster_id=None,
    ex_cpu_specification=None,
    ex_memory_gb=None,
    ex_primary_nic_private_ipv4=None,
    ex_primary_nic_vlan=vlan,
    ex_primary_nic_network_adapter=None,
    ex_additional_nics=None,
    ex_disks=None,
    ex_tagid_value_pairs=ex_tagid_value_pairs,
    ex_tagname_value_pairs=None,
)

pprint(node)
