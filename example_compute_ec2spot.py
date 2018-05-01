import os
import time
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeImage
from libcloud.compute.types import NodeState

SIZE_ID = 't2.micro'
AMI_ID = 'ami-4e79ed36'
REGION = 'us-west-2'
KEYPAIR_NAME = 'mykey'
SECURITY_GROUP_NAMES = ['default', 'ssh']
NODE_NAME = 'test-spot-node'

def create_spot_request(accessid, secretkey):
    cls = get_driver(Provider.EC2)
    driver = cls(accessid, secretkey, region=REGION)

    sizes = driver.list_sizes()
    size = [s for s in sizes if s.id == SIZE_ID][0]
    image = NodeImage(id=AMI_ID, name=None, driver=driver)

    # create the spot instance
    node = driver.create_node(
        image=image,
        size=size,
        ex_spot_market=True,
        ex_spot_price=0.005,
        name=NODE_NAME,
        keyname=KEYPAIR_NAME,
        security_groups=SECURITY_GROUP_NAMES)

    print("Spot instance created: '%s" % node.id)
    assert node.extra.get('instance_lifecycle') == 'spot'
    print("Destroying node...")
    driver.destroy_node(node)
    while node.state != NodeState.TERMINATED:
        print("...waiting to be terminated (State: %s)" % node.state)
        node = driver.list_nodes(ex_node_ids=[node.id])[0]
        time.sleep(5)

def main():
    accessid = os.getenv('ACCESSID')
    secretkey = os.getenv('SECRETKEY')

    if accessid and secretkey:
        create_spot_request(accessid, secretkey)
    else:
        print('ACCESSID and SECRETKEY are sourced from the environment')

if __name__ == "__main__":
    main()
