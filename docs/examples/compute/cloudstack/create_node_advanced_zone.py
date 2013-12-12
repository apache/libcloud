# List the guest networks
# This returns a list of CloudStackNetwork objects
nets=driver.ex_list_networks()

# List the images/templates available
# This returns a list of NodeImage objects
images=driver.list_images()

# List the instance types
# This returns a list of NodeSize objects
sizes=driver.list_sizes()

# Create the node
# This returns a Node object
node=driver.create_node(name='libcloud',image=images[0],size=sizes[0],network=[nets[0]])

# The node has a private IP in the guest network used , no public IPs and no rules
node.extra
{'created': u'2013-12-12T08:51:51-0500',
 'ip_addresses': [],
 'ip_forwarding_rules': [],
 'keyname': None,
 'password': u'dF7jsehug',
 'port_forwarding_rules': [],
 'securitygroup': [],
 'zoneid': 'd06193b2-7980-4ad1-b5d8-7b2f2eda63c3'}

node.private_ips
[u'10.1.1.136']

