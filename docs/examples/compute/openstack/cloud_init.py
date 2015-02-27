from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


cloud_init_config = """
#cloud-config

packages:

 - nginx

runcmd:

 - service nginx start

"""


OpenStack = get_driver(Provider.OPENSTACK)
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_url='http://192.168.1.101:5000',
                   ex_force_auth_version='2.0_password')

image = driver.get_image('image_id')
size = driver.list_sizes()[0]

node = driver.create_node(name='cloud_init', image=image, size=size,
                          ex_userdata=cloud_init_config, ex_config_drive=True)
