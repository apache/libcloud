# Allocate a public IP
# This returns a CloudStackAddress object
driver.ex_allocate_public_ip()

# You can now see this address when listing public IPs
ip = driver.ex_list_public_ips()[0]

# Create a port forwarding rule for the node
# This returns a CloudStackPortForwardingRule object
rule = conn.ex_create_port_forwarding_rule(ip, 22, 22, 'TCP', node)
pprint(rule)

# The node now has a public IP and a rule associated to it
print node
print node.extra
