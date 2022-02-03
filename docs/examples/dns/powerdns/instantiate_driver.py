from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.POWERDNS)

# powerdns3.example.com is running PowerDNS v3.x.
driver = cls(key="changeme", host="powerdns3.example.com", port=8081)

# OR:

# powerdns4.example.com is running PowerDNS v4.x, so it uses api_version v1.
driver = cls(key="changeme", host="powerdns4.example.com", port=8081, api_version="v1")
