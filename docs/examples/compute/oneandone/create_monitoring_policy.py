import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

ports = [
    {
        "protocol": "TCP",
        "port": 443,
        "alert_if": "NOT_RESPONDING",
        "email_notification": True,
    }
]

processes = [{"process": "httpdeamon", "alert_if": "NOT_RUNNING", "email_notification": False}]
thresholds = {
    "cpu": {
        "warning": {"value": 90, "alert": False},
        "critical": {"value": 95, "alert": False},
    },
    "ram": {
        "warning": {"value": 90, "alert": False},
        "critical": {"value": 95, "alert": False},
    },
    "disk": {
        "warning": {"value": 80, "alert": False},
        "critical": {"value": 90, "alert": False},
    },
    "transfer": {
        "warning": {"value": 1000, "alert": False},
        "critical": {"value": 2000, "alert": False},
    },
    "internal_ping": {
        "warning": {"value": 50, "alert": False},
        "critical": {"value": 100, "alert": True},
    },
}

try:
    monitoring_policy = drv.ex_create_monitoring_policy(
        name="Monitoring Policy",
        ports=ports,
        thresholds=thresholds,
        processes=processes,
        description="Monitoring Policy Description",
        email="test@test.com",
        agent=True,
    )
    print(monitoring_policy)
except Exception as e:
    print(e)
