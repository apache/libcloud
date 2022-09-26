import libcloud.security
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Get nttcis driver
libcloud.security.VERIFY_SSL_CERT = True
cls = get_driver(Provider.NTTCIS)
driver = cls("myusername", "mypassword", region="eu")
image_name = "SLES 12 64-bit"
images = driver.list_images(location="EU6")
image = [i for i in images if i.name == image_name][0]
domain_name = "test_1"
domains = driver.ex_list_network_domains(location="EU6")
net_domain = [d for d in domains if d.name == domain_name][0]
psswd = "mypassword123!"
vlan_name = "vlan1"
vlans = driver.ex_list_vlans()
vlan = [v for v in vlans if v.name == vlan_name][0]
new_node = driver.create_node(
    "Suse_12",
    image,
    psswd,
    ex_description="Customized_Suse server",
    ex_network_domain=net_domain,
    ex_primary_nic_vlan=vlan,
    ex_primary_nic_network_adapter="VMXNET3",
    ex_memory_gb=8,
)
driver.ex_wait_for_state("running", driver.ex_get_node_by_id, 20, 420, new_node.id)
