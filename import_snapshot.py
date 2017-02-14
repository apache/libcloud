import pdb
from pprint import pprint
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2_ACCESS_ID = 'Your access key'
EC2_SECRET_KEY = 'Your Secret key'

EC2Driver = get_driver(Provider.EC2)
driver = EC2Driver(EC2_ACCESS_ID, EC2_SECRET_KEY)
pprint("Hello")
disk_container = [{'Description': 'amisstea-test2',
                  'Format': 'raw',
                  'UserBucket': {
                    'S3Bucket': 'amisstea-test',
                    'S3Key': 'rhel-server-ec2-7.3-6.x86_64.raw'
                  }}]
pdb.set_trace()
obj = driver.ex_import_snapshot(None,None,None,disk_container,None,None)
pprint(obj)
pprint('Printed something?')


