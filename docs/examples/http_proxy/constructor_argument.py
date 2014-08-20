from libcloud.compute.drivers.dreamhost import DreamhostConnection

PROXY_URL_NO_AUTH = 'http://<proxy hostname>:<proxy port>'
PROXY_URL_BASIC_AUTH = 'http://<user>:<pass>@<proxy hostname>:<proxy port>'

conn = DreamhostConnection(host='dreamhost.com', port=443,
                           timeout=None, proxy_url=PROXY_URL_NO_AUTH)
