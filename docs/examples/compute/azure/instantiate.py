from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.AZURE)
driver = cls(subscription_id="subscription-id", key_file="/path/to/azure_cert.pem")
