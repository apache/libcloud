import libcloud.security
from libcloud.common.nttcis import NttCisPort, NttCisIpAddress, NttCisFirewallAddress
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Get nttcis driver
libcloud.security.VERIFY_SSL_CERT = True
cls = get_driver(Provider.NTTCIS)
driver = cls("myusername", "mypassword", region="eu")
# Get location
location = driver.ex_get_location_by_id(id="EU6")

# Get network domain by location
networkDomainName = "sdk_test_1"
network_domains = driver.ex_list_network_domains(location=location.id)
my_network_domain = [d for d in network_domains if d.name == networkDomainName][0]

# Create an instance of NttCisFirewallAddress for source
source_firewall_address = NttCisFirewallAddress(any_ip="ANY")

# Create an instance of NttCisIpAddress for an Address List for the destination
address_list_name = "sdk_test_address_list"
description = "A test address list"
ip_version = "IPV4"
# An optional prefix list can be specified as a named argument, prefix_size=
address_obj = [NttCisIpAddress("10.2.0.1", end="10.2.0.11")]

result = driver.ex_create_ip_address_list(
    my_network_domain.id, address_list_name, description, ip_version, address_obj
)

try:
    assert result is True
except Exception:
    raise RuntimeError("Something went wrong in address list creation.")
else:
    addr_list = driver.ex_list_ip_address_list(my_network_domain.id)
    addr_list = [al for al in addr_list if al.name == address_list_name][0]

# Instead of a single port or list of ports, create a port
# list for the destianation
port_list_name = "sdk_test_port_list"
description = "A test port list"

# rerquires an instance of NttCisPort object
ports = [NttCisPort(begin="8000", end="8080")]
result = driver.ex_create_portlist(my_network_domain.id, port_list_name, description, ports)

try:
    assert result is True
except Exception:
    raise RuntimeError("Something went wrong in address list creation.")
else:
    port_list = driver.ex_list_portlist(my_network_domain.id)
    port_list = [pl for pl in port_list if pl.name == port_list_name][0]

# Create an instance of NttCisFirewallAddress for destination
dest_firewall_address = NttCisFirewallAddress(
    address_list_id=addr_list.id, port_list_id=port_list.id
)

# Finally create firewall rule
rule = driver.ex_create_firewall_rule(
    my_network_domain.id,
    "sdk_test_firewall_rule",
    "ACCEPT_DECISIVELY",
    "IPV4",
    "TCP",
    source_firewall_address,
    dest_firewall_address,
    "LAST",
)
print(rule)
