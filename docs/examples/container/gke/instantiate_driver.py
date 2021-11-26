from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.GKE)

conn = cls(
    "testaccount-XXX@testproject.iam.gserviceaccount.com",
    "libcloud.json",
    project="testproject",
)

conn.list_clusters()
