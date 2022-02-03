from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")

check = driver.ex_check_availability("wazzlewobbleflooble.com")
if check.available is True:
    print("Domain is available for {} {}".format(check.price, check.currency))
else:
    print("Domain is taken")
