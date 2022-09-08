from pprint import pprint

import libcloud.security
from libcloud.common.nttcis import NttCisFirewallAddress
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Get nttcis driver
libcloud.security.VERIFY_SSL_CERT = True
cls = get_driver(Provider.NTTCIS)
driver = cls("myusername", "mypassword", region="eu")

domain_name = "sdk_test_1"
domains = driver.ex_list_network_domains(location="EU6")
net_domain = [d for d in domains if d.name == domain_name]
source_firewall_address = NttCisFirewallAddress(any_ip="ANY")
dest_firewall_address = NttCisFirewallAddress(
    ip_address="10.2.0.0", ip_prefix_size="16", port_begin="8000", port_end="8080"
)

rule = driver.ex_create_firewall_rule(
    net_domain[0],
    "sdk_test_firewall_rule_2",
    "ACCEPT_DECISIVELY",
    "IPV4",
    "TCP",
    source_firewall_address,
    dest_firewall_address,
    "LAST",
)
pprint(rule)
