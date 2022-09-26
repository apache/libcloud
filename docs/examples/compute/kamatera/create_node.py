from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.KAMATERA)
driver = cls("KAMATERA API CLIENT ID", "KAMATERA API SECRET")

# select a location

locations = {location.id: location for location in driver.list_locations()}
for location in locations.values():
    print(location)

# <NodeLocation: id=AS, name=Hong Kong, country=China
# <NodeLocation: id=CA-TR, name=Toronto, country=Canada
# <NodeLocation: id=EU, name=Amsterdam, country=The Netherlands
# <NodeLocation: id=EU-FR, name=Frankfurt, country=Germany
# <NodeLocation: id=EU-LO, name=London, country=United Kingdom
# <NodeLocation: id=IL, name=Rosh Haayin, country=Israel
# <NodeLocation: id=IL-JR, name=Jerusalem, country=Israel
# <NodeLocation: id=IL-PT, name=Petach Tikva, country=Israel
# <NodeLocation: id=IL-RH, name=Rosh Haayin 2, country=Israel
# <NodeLocation: id=IL-TA, name=Tel Aviv, country=Israel
# <NodeLocation: id=US-NY2, name=New York, country=United States
# <NodeLocation: id=US-SC, name=Santa Clara, country=United States
# <NodeLocation: id=US-TX, name=Texas, country=United States

location = locations["US-NY2"]

# get the capabilities for this location

capabilities = driver.ex_list_capabilities(location)

# choose a cpu type

cpuTypes = {cpuType["id"]: cpuType for cpuType in capabilities["cpuTypes"]}
for cpuType in cpuTypes.values():
    print("{}: {}".format(cpuType["name"], cpuType["description"]))

# Type B - General Purpose: Server CPUs are assigned to a dedicated physical
#          CPU Thread with reserved resources guaranteed.
# Type D - Dedicated: Server CPU are assigned to a dedicated physical CPU Core
#          (2 threads) with reserved resources guaranteed.
# Type T - Burstable: Server CPUs are assigned to a dedicated physical CPU
#          thread with reserved resources guaranteed.
# Type A - Availability: Server CPUs are assigned to a non-dedicated physical
#          CPU thread with no resources guaranteed.

cpuType = cpuTypes["B"]

# choose number of cpu cores

print(cpuType["cpuCores"])

# [1, 2, 4, 6, 8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72]

cpuCores = 2

# choose amount of RAM

print(cpuType["ramMB"])

# [256, 512, 1024, 2048, 3072, 4096, 6144, 8192, 10240, 12288, 16384, 24576,
#  32768, 49152, 65536, 98304, 131072, 200704, 262144, 327680, 393216]

ramMB = 2048

# choose disk sizes

print(capabilities["diskSizeGB"])

# [5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 150, 200, 250, 300, 350, 400, 450,
#  500, 600, 700, 800, 900, 1000, 1500, 2000, 3000, 4000]

# primary disk size

diskSizeGB = 20

# additional disks (up to 3 additional disks)

extraDiskSizesGB = [100, 200]

# choose a billing cycle

billingCycle = driver.EX_BILLINGCYCLE_MONTHLY
# billingCycle = driver.EX_BILLINGCYCLE_HOURLY

# in case of monthly billing cycle, choose traffic package

print(capabilities["monthlyTrafficPackage"])

# {'b50': '50Mbit/sec unmetered on 10Gbit/sec port',
#  't5000': '5000GB/month on 10Gbit/sec port'}

monthlyTrafficPackage = "t5000"

# create node size object

size = driver.ex_get_size(
    ramMB,
    diskSizeGB,
    cpuType["id"],
    cpuCores,
    extraDiskSizesGB=extraDiskSizesGB,
    monthlyTrafficPackage=monthlyTrafficPackage,
)

# choose an OS image

images = {image.id: image for image in driver.list_images(location)}

for image in images.values():
    print("{}: {}".format(image.id, image.name))

# list is shortened, actual list will vary and provide more OS image options

# US-NY2:6000C2987c9641fd2619a149ba2ca01a: CentOS 8.0 64-bit - Minimal
# US-NY2:6000C29b85c6367d215d403f44c28f48: CentOS 8.0 64-bit - Basic Server
# US-NY2:6000C29bb8fde673f515caf9bed695a1: Debian version 8.9 (jessie) 64-bit
# US-NY2:6000C29e4131d66b806c25c48ab0b810: FreeBSD 12.1 64-bit
# US-NY2:6000C2983bdd8b531ecfc6d892a35aa4: FreeBSD 11.1 32-bit
# US-NY2:6000C29a5a7220dcf84716e7bba74215: Ubuntu Server version 18.04 LTS
# US-NY2:6000C298bbb2d3b6e9721f4f4f3c5bf0: Ubuntu Server version 16.04 LTS

image = images["US-NY2:6000C29a5a7220dcf84716e7bba74215"]

# set network configurations (up to 4 interfaces can be added)

networks = []

# add a wan to get a public IP

networks.append({"name": "wan", "ip": "auto"})

# add a vlan interface to get a private IP
# vlan network name and ip should be configured in the Kamatera console

networks.append({"name": "12345-my-vlan", "ip": "auto"})

# create node

node = driver.create_node(
    name="test_libcloud_server",
    size=size,
    image=image,
    location=location,
    ex_networks=networks,
    ex_dailybackup=False,  # create daily backups for the node?
    ex_managed=False,  # provide managed support for the node?
    ex_billingcycle=billingCycle,
)

# get the node SSH connection details

print("root@{}  /  {}".format(node.public_ips[0], node.extra["generated_password"]))
