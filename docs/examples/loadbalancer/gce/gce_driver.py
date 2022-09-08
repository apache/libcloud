from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.loadbalancer.types import Provider as LBProvider
from libcloud.loadbalancer.providers import get_driver as lb_get_driver

ComputeEngine = get_driver(Provider.GCE)
gce_driver = ComputeEngine(
    "service_account_email_or_client_id",
    "pem_file_or_client_secret",
    project="your_project_id",
)

LoadBalancer = lb_get_driver(LBProvider.GCE)
lb_driver = LoadBalancer(gce_driver=gce_driver)
