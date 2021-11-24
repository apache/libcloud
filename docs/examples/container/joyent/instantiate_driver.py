from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.JOYENT)

conn = cls(
    host="us-east-1.docker.joyent.com",
    port=2376,
    key_file="key.pem",
    cert_file="~/.sdc/docker/admin/ca.pem",
)

conn.list_images()
