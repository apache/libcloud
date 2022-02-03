from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ComputeEngine = get_driver(Provider.GCE)
driver = ComputeEngine(
    "your_client_id",
    "your_client_secret",
    datacenter="us-central1-a",
    project="your_project_id",
)
