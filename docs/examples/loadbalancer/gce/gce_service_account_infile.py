from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

credentials = {
    "type": "service_account",
    "project_id": "my_project",
    "private_key": "-----BEGIN PRIVATE KEY-----\nmy_private_key_data\n"
    "-----END PRIVATE KEY-----\n",
    "client_email": "my_email",
}

LoadBalancer = get_driver(Provider.GCE)
driver = LoadBalancer("your_service_account_email", credentials, project="your_project_id")
