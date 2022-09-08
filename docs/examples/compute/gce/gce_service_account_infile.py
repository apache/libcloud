from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

credentials = {
    "type": "service_account",
    "project_id": "my_project",
    "private_key": "-----BEGIN PRIVATE KEY-----\nmy_private_key_data\n"
    "-----END PRIVATE KEY-----\n",
    "client_email": "my_email",
}

ComputeEngine = get_driver(Provider.GCE)
driver = ComputeEngine("your_service_account_email", credentials, project="your_project_id")
