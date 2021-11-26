import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

rules = [
    {"protocol": "TCP", "port_balancer": 80, "port_server": 80, "source": "0.0.0.0"},
    {
        "protocol": "TCP",
        "port_balancer": 9999,
        "port_server": 8888,
        "source": "0.0.0.0",
    },
]

try:
    shared_storage = drv.ex_create_load_balancer(
        name="Test Load Balancer",
        method="ROUND_ROBIN",
        rules=rules,
        persistence=False,
        persistence_time=1200,
        health_check_test="TCP",
        health_check_interval=40,
    )

    print(shared_storage)
except Exception as e:
    print(e)
