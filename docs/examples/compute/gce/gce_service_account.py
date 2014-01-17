from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ComputeEngine = get_driver(Provider.GCE)
driver = ComputeEngine('your_service_account_email', 'path_to_pem_file',
                       project='your_project_id')
