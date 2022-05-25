from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.KAMATERA)
driver = cls("KAMATERA API CLIENT ID", "KAMATERA API SECRET")

# list all nodes (quick operation, provides only basic details for each node)

nodes = driver.list_nodes()

# get more details for a specific node

node = driver.list_nodes(ex_id=nodes[0].id)[0]
print(node)

# list nodes with full details based on regex of node name

nodes = driver.list_nodes(ex_name_regex="test_libcloud.*")
print(nodes[0])

# <Node: uuid=9566552b254b42063e87ba644a982d330602b06c,
#        name=test_libcloud_server, state=RUNNING,
#        public_ips=['138.128.241.118'], private_ips=[], provider=Kamatera

print(nodes[0].extra)

# {'billingcycle': 'monthly', 'priceOn': '25', 'priceOff': '25',
#  'location': <NodeLocation: id=US-NY2>, 'dailybackup': False,
#  'managed': False}

# list all nodes with full details (slower operation)

nodes = driver.list_nodes(ex_full_details=True)

node = nodes[0]

# run operations

driver.start_node(node)
driver.stop_node(node)
driver.reboot_node(node)
driver.destroy_node(node)
