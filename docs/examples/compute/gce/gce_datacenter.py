from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ComputeEngine = get_driver(Provider.GCE)
# Datacenter is set to 'us-central1-a' as an example, but can be set to any
# zone, like 'us-central1-b' or 'europe-west1-a'
driver = ComputeEngine(
    "your_service_account_email",
    "path_to_pem_file",
    datacenter="us-central1-a",
    project="your_project_id",
)
