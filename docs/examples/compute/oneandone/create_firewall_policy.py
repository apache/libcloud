import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

my_rules = [
    {"protocol": "TCP", "port_from": 80, "port_to": 80, "source": "0.0.0.0"},
    {
        "description": "Testing firewall improvements",
        "protocol": "TCP",
        "port": 443,
        "source": "0.0.0.0",
    },
]

print(type(my_rules))

try:
    fw_policy = drv.ex_create_firewall_policy(
        name="Firewall Policy", rules=my_rules, description="FW Policy Description"
    )
    print(fw_policy)
except Exception as e:
    print(e)
