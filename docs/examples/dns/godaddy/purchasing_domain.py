from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")

# Get the JSON schema for the domain
schema = driver.ex_get_purchase_schema("com")

# Use this schema to prepare a purchase request document

# Load a JSON document that has the completed purchase request
file = open("purchase_request.json")
document = file.read()
order = driver.ex_purchase_domain(document)
print("Made request : order ID : %s" % order.order_id)
