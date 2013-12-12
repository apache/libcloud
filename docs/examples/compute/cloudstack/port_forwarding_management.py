# Allocate a public IP
# This returns a CloudStackAddress object
driver.ex_allocate_public_ip()
<libcloud.compute.drivers.cloudstack.CloudStackAddress at 0x10c4c51d0>

# You can now see this address when listing public IPs
ip=driver.ex_list_public_ips()[0]

# Create a port forwarding rule for the node
# This returns a CloudStackPortForwardingRule object
rule=conn.ex_create_port_forwarding_rule(ip,22,22,'TCP',node)
rule
<libcloud.compute.drivers.cloudstack.CloudStackPortForwardingRule at 0x10c4c5a90>

# The node now has a public IP and a rule associated to it
node
<Node: uuid=9e14e050f83ed4d4f5ad325a8c6d4f0b8078c0ca, name=libcloud, state=0, public_ips=[u'33.33.33.44'], provider=CloudStack ...>
node.extra
{'created': u'2013-12-12T08:51:51-0500',
 'ip_addresses': [],
 'ip_forwarding_rules': [],
 'keyname': None,
 'password': u'dF7jsehug',
 'port_forwarding_rules': [<libcloud.compute.drivers.cloudstack.CloudStackPortForwardingRule at 0x10c4c5a90>],
 'securitygroup': [],
 'zoneid': 'd06193b2-7980-4ad1-b5d8-7b2f2eda63c3'}
