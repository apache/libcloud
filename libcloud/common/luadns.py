import base64


from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.utils.py3 import b

__all__ = [
    'API_HOST',
    'LuadnsException',
    'LuadnsResponse',
    'LuadnsConnection'
]

# Endpoint for luadns api
API_HOST = 'api.luadns.com'


class LuadnsResponse(JsonResponse):
    errors = []
    objects = []

    def __init__(self, response, connection):
        super(LuadnsResponse, self).__init__(response=response,
                                             connection=connection)
        self.errors, self.objects = self.parse_body_and_errors()
        if not self.success():
            raise LuadnsException(code=self.status,
                                  message=self.errors.pop()['message'])

    def parse_body_and_errors(self):
        js = super(LuadnsResponse, self).parse_body()
        if 'message' in js:
            self.errors.append(js)
        else:
            self.objects.append(js)

        return self.errors, self.objects

    def success(self):
        return len(self.errors) == 0


class LuadnsConnection(ConnectionUserAndKey):
    host = API_HOST
    responseCls = LuadnsResponse

    def add_default_headers(self, headers):
        b64string = b('%s:%s' % (self.user_id, self.key))
        encoded = base64.b64encode(b64string).decode('utf-8')
        authorization = 'Basic ' + encoded

        headers['Accept'] = 'application/json'
        headers['Authorization'] = authorization

        return headers


class LuadnsException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "%s %s" % (self.code, self.message)

    def __repr__(self):
        return "Luadns %s %s" % (self.code, self.message)
