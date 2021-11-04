from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

subscription = driver.ex_create_subscription(
    amount=1, period="30 days", resource="vlan", auto_renew=True
)
print(subscription)
