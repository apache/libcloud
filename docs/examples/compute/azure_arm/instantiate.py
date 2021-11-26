from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.AZURE_ARM)
driver = cls(
    tenant_id="tenant_id",
    subscription_id="subscription_id",
    key="application_id",
    secret="password",
)
