from libcloud.common.base import ConnectionKey, JsonResponse


__all__ = [
    'API_HOST',
    'NsOneException',
    'NsOneResponse',
    'NsOneConnection'
]

# Endpoint for nsone api
API_HOST = 'api.nsone.net'


class NsOneResponse(JsonResponse):
    errors = []
    objects = []

    def __init__(self, response, connection):
        super(NsOneResponse, self).__init__(response=response,
                                            connection=connection)
        self.errors, self.objects = self.parse_body_and_errors()
        if not self.success():
            raise NsOneException(code=self.status,
                                 message=self.errors.pop()['message'])

    def parse_body_and_errors(self):
        js = super(NsOneResponse, self).parse_body()
        if 'message' in js:
            self.errors.append(js)
        else:
            self.objects.append(js)

        return self.errors, self.objects

    def success(self):
        return len(self.errors) == 0


class NsOneConnection(ConnectionKey):
    host = API_HOST
    responseCls = NsOneResponse

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'application/json'
        headers['X-NSONE-KEY'] = self.key

        return headers


class NsOneException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "%s %s" % (self.code, self.message)

    def __repr__(self):
        return "NsOneException %s %s" % (self.code, self.message)
