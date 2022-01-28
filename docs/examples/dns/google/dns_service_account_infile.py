from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

credentials = {
    "type": "service_account",
    "project_id": "my_project",
    "private_key": "-----BEGIN PRIVATE KEY-----\nmy_private_key_data\n"
    "-----END PRIVATE KEY-----\n",
    "client_email": "my_email",
}

DNSDriver = get_driver(Provider.GOOGLE)
driver = DNSDriver("your_service_account_email", credentials, "your_project_id")
