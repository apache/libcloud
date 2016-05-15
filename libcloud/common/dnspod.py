from libcloud.common.base import ConnectionKey, JsonResponse


__all__ = [
    'API_HOST',
    'DNSPodException',
    'DNSPodResponse',
    'DNSPodConnection'
]

# Endpoint for dnspod api
API_HOST = 'api.dnspod.com'


class DNSPodResponse(JsonResponse):
    errors = []
    objects = []

    def __init__(self, response, connection):
        super(DNSPodResponse, self).__init__(response=response,
                                             connection=connection)
        self.errors, self.objects = self.parse_body_and_errors()
        if not self.success():
            raise DNSPodException(code=self.status,
                                  message=self.errors.pop()
                                  ['status']['message'])

    def parse_body_and_errors(self):
        js = super(DNSPodResponse, self).parse_body()
        if 'status' in js and js['status']['code'] != '1':
            self.errors.append(js)
        else:
            self.objects.append(js)

        return self.errors, self.objects

    def success(self):
        return len(self.errors) == 0


class DNSPodConnection(ConnectionKey):
    host = API_HOST
    responseCls = DNSPodResponse

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Accept'] = 'text/json'
        headers['User-Agent'] = \
            'dnspod-python/0.01 (im@chuangbo.li; DNSPod.CN API v2.8)'

        return headers


class DNSPodException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "%s %s" % (self.code, self.message)

    def __repr__(self):
        return "DNSPodException %s %s" % (self.code, self.message)
