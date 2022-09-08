from pprint import pprint

import libcloud

cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.CLOUDSCALE)

TOKEN = "3pjzjh3h3rfynqa4iemvtvc33pyfzss2"
driver = cls(TOKEN)

sizes = driver.list_sizes()
images = driver.list_images()
pprint(sizes)
pprint(images)

new_node = driver.create_node(
    name="hello-darkness-my-old-friend",
    size=sizes[0],
    image=images[0],
    ex_create_attr=dict(
        ssh_keys=["ssh-rsa AAAAB3Nza..."],
        use_private_network=True,
    ),
)
pprint(new_node)
