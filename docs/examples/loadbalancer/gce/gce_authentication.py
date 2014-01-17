from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

LoadBalancer = get_driver(Provider.GCE)
driver = LoadBalancer('service_account_email_or_client_id',
                      'pem_file_or_client_secret',
                      project='your_project_id')
