from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# This example assumes you are running on an instance within Google
# Compute Engine. As such, the only parameter you need to specify is
# the Project ID. The GCE driver will the consult GCE's internal
# metadata service for an authorization token.
ComputeEngine = get_driver(Provider.GCE)
driver = ComputeEngine(project='your_project_id')
