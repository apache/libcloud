from libcloud.compute.base import NodeAuthPassword
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ECSDriver = get_driver(Provider.ALIYUN_ECS)

region = "cn-hangzhou"
access_key_id = "CHANGE IT"
access_key_secret = "CHANGE IT"

driver = ECSDriver(access_key_id, access_key_secret, region=region)

# Query the size ecs.t1.small
sizes = driver.list_sizes()
t1_small = sizes[1]
# Query the first ubuntu OS image
images = driver.list_images()
for each in images:
    if "ubuntu" in each.id.lower():
        ubuntu = each
        break
else:
    ubuntu = images[0]
# Query the default security group
sg = driver.ex_list_security_groups()[0]

# Create a cloud type data disk which is 5GB and deleted with the node
data_disk = {
    "size": 5,
    "category": driver.disk_categories.CLOUD,
    "disk_name": "data_disk1",
    "delete_with_instance": True,
}

# Set a password to access the guest OS
auth = NodeAuthPassword("P@$$w0rd")

# Create the node
node = driver.create_node(
    image=ubuntu,
    size=t1_small,
    name="test_node",
    ex_security_group_id=sg.id,
    ex_internet_charge_type=driver.internet_charge_types.BY_TRAFFIC,
    ex_internet_max_bandwidth_out=1,
    ex_data_disks=data_disk,
    auth=auth,
)

# Reboot the node
node.reboot()

# Stop the node
driver.ex_stop_node(node)

# Start the node
driver.ex_start_node(node)

# Destroy the node
node.destroy()
