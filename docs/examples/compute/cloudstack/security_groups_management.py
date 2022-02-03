from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EXOSCALE)
driver = cls("api key", "api secret key")

# List all security groups
sg = driver.ex_list_security_groups()
pprint(sg)

# Create a new security group.
security_group = driver.ex_create_security_group(name="test-security-group")
pprint(security_group)

# Authorize an ingress rule on a security group
# If `startport` is used alone, this will be the only port open
# If `endport` is also used then the entire range will be authorized
sg = driver.ex_authorize_security_group_ingress(
    securitygroupname="test-security-group",
    protocol="tcp",
    startport="22",
    cidrlist="0.0.0.0/0",
)

pprint(sg)

# Delete a security group we have previously created
status = driver.ex_delete_security_group(name="test-security-group")
pprint(status)
