from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

#
# Instantiate driver
#
username = "your account username"
password = "your account password"
host = "onapp.test"

cls = get_driver(Provider.ONAPP)
driver = cls(key=username, secret=password, host=host)

#
# Create node
#
name = "virtual_servers_name"  # user-friendly VS description
memory = 2 * 1024  # amount of RAM assigned to the VS in MB
cpus = 2  # number of CPUs assigned to the VS
cpu_shares = 100
# For KVM hypervisor the CPU priority value is always 100. For XEN, set a
# custom value. The default value for XEN is 1
hostname = "vshostname"  # set the host name for this VS
template_id = 8  # the ID of a template from which a VS should be built
primary_disk_size = 100  # set the disk space for this VS
swap_disk_size = None  # set swap space

# optional parameter, but recommended
rate_limit = None
# set max port speed. If none set, the system sets port speed to unlimited

node = driver.create_node(
    name=name,
    ex_memory=memory,
    ex_cpus=cpus,
    ex_cpu_shares=cpu_shares,
    ex_hostname=hostname,
    ex_template_id=template_id,
    ex_primary_disk_size=primary_disk_size,
    ex_swap_disk_size=swap_disk_size,
    ex_rate_limit=rate_limit,
)

#
# List nodes
#
for node in driver.list_nodes():
    print(node)

#
# Destroy node
#
identifier = "nodesidentifier"

(node,) = (n for n in driver.list_nodes() if n.id == identifier)

driver.destroy_node(node)

#
# List images
#
for image in driver.list_images():
    print(image)

#
# List key pairs
#
for key_pair in driver.list_key_pairs():
    print(key_pair)

#
# Get key pair
#
id = 2  # ID of key pair
key_pair = driver.get_key_pair(id)
print(key_pair)

#
# Import key pair from string
#
name = "example"  # this param is unused
key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8uuUq..."
key_pair = driver.import_key_pair_from_string(name, key)

#
# Import key pair from file
#
driver.import_key_pair_from_file("example", "~/.ssh/id_rsa.pub")

#
# Delete key pair
#
key_pair = driver.list_key_pairs()[0]
driver.delete_key_pair(key_pair)
