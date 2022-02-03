from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# This example assumes you are running on an instance within Google
# Compute Engine. As such, the only value you need to specify is
# the Project ID. The GCE driver will the consult GCE's internal
# metadata service for an authorization token.
#
# You must still place placeholder empty strings for user_id / key
# due to the nature of the driver's __init__() params.
ComputeEngine = get_driver(Provider.GCE)
driver = ComputeEngine("", "", project="your_project_id", datacenter="us-central1-a")
