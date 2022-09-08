from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

name = "test node"
size = driver.list_sizes()[0]

drives = driver.ex_list_library_drives()
image = [drive for drive in drives if drive.name == "FreeBSD 8.2" and drive.media == "cdrom"][0]

# 1. Create a node
node = driver.create_node(name=name, size=size, image=image)
print(node)

# 2. Wait for node to come online
driver.wait_until_running(nodes=[node])

# 3. Enable and obtain VNC URL so we can connect to the VNC server and walk
# through the installation process
tunnel_url = driver.ex_open_vnc_tunnel(node=node)

print("VNC tunnel URL: %s" % (tunnel_url))
print("VNC password: %s" % (node.extra["vnc_password"]))
