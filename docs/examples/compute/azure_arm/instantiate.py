from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.AZURE_ARM)
driver = cls(tenant_id='$tenantId',
             subscription_id='$subscriptionId',
             key='$client', secret='$password')
