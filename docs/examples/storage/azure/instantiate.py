from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

cls = get_driver(Provider.AZURE_BLOBS)

driver = cls(key="your storage account name", secret="your access key")
