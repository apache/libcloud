from libcloud.compute.drivers.dreamhost import DreamhostConnection

PROXY_URL = 'http://<proxy hostname>:<proxy port>'

conn = DreamhostConnection(host='dreamhost.com', port=443,
                           timeout=None, proxy_url=PROXY_URL)
