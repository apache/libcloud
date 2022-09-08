from build.lib.libcloud.storage.types import Provider
from build.lib.libcloud.storage.providers import get_driver

cls = get_driver(Provider.AZURE_BLOBS)

driver = cls(
    key="your storage account name",
    secret="your service principal secret key",
    tenant_id="your tenant id",
    identity="your service principal application id",
    auth_type="azureAd",
)
