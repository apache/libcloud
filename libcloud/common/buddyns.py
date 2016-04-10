from libcloud.common.base import ConnectionKey, JsonResponse


__all__ = [
    'API_HOST',
    'BuddyNSException',
    'BuddyNSResponse',
    'BuddyNSConnection'
]

# Endpoint for buddyns api
API_HOST = 'www.buddyns.com'


class BuddyNSResponse(JsonResponse):
    errors = []
    objects = []

    def __init__(self, response, connection):
        super(BuddyNSResponse, self).__init__(response=response,
                                              connection=connection)
        self.errors, self.objects = self.parse_body_and_errors()
        if not self.success():
            raise BuddyNSException(code=self.status,
                                   message=self.errors.pop()['detail'])

    def parse_body_and_errors(self):
        js = super(BuddyNSResponse, self).parse_body()
        if 'detail' in js:
            self.errors.append(js)
        else:
            self.objects.append(js)

        return self.errors, self.objects

    def success(self):
        return len(self.errors) == 0


class BuddyNSConnection(ConnectionKey):
    host = API_HOST
    responseCls = BuddyNSResponse

    def add_default_headers(self, headers):
        headers['content-type'] = 'application/json'
        headers['Authorization'] = 'Token' + ' ' + self.key

        return headers


class BuddyNSException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "%s %s" % (self.code, self.message)

    def __repr__(self):
        return "BuddyNSException %s %s" % (self.code, self.message)
