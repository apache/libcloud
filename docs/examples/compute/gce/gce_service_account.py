from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ComputeEngine = get_driver(Provider.GCE)
# Note that the 'PEM file' argument can either be the JSON format or
# the P12 format.
driver = ComputeEngine(
    "your_service_account_email",
    "path_to_pem_file",
    project="your_project_id",
    datacenter="us-central1-a",
)
