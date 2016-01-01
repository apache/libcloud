from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

import libcloud.security
libcloud.security.VERIFY_SSL_CERT = False

cls = get_driver(Provider.ECS)

conn = cls(access_id='AKIAI7OR4GWEEPRIFBBA', secret='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', region='ap-southeast-2')
conn.connection.set_http_proxy(proxy_url='http://localhost:8888')

print(conn.list_containers())
