from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

FILE_PATH = "/home/user/myfile.tar.gz"

cls = get_driver(Provider.SCALEWAY)

driver = cls("api key", "api secret key", region="fr-par")

container = driver.get_container(container_name="<your-bucket-name>")

extra = {
    "meta_data": {"owner": "myuser", "created": "2001-05-25"},
    "acl": "public-read",
}

with open(FILE_PATH, "rb") as iterator:
    obj = driver.upload_object_via_stream(
        iterator=iterator, container=container, object_name="backup.tar.gz", extra=extra
    )
