from libcloud.common.base import ConnectionKey, JsonResponse


__all__ = [
    'API_HOST',
    'VultrConnection',
    'VultrException',
    'VultrResponse',
]

# Endpoint for the Vultr API
API_HOST = 'api.vultr.com'


class VultrResponse(JsonResponse):

    objects = None
    error_dict = {}
    errors = None
    ERROR_CODE_MAP = {

        400: "Invalid API location. Check the URL that you are using.",
        403: "Invalid or missing API key. Check that your API key is present" +
             " and matches your assigned key.",
        405: "Invalid HTTP method. Check that the method (POST|GET) matches" +
             " what the documentation indicates.",
        412: "Request failed. Check the response body for a more detailed" +
             " description.",
        500: "Internal server error. Try again at a later time.",
        503: "Rate limit hit. API requests are limited to an average of 1/s." +
             " Try your request again later.",

    }

    def __init__(self, response, connection):

        self.errors = []
        super(VultrResponse, self).__init__(response=response,
                                            connection=connection)
        self.objects, self.errors = self.parse_body_and_errors()
        if not self.success():
            raise self._make_excp(self.errors[0])

    def parse_body_and_errors(self):
        """
        Returns JSON data in a python list.
        """
        json_objects = []
        errors = []

        if self.status in self.ERROR_CODE_MAP:
            self.error_dict['ERRORCODE'] = self.status
            self.error_dict['ERRORMESSAGE'] = self.ERROR_CODE_MAP[self.status]
            errors.append(self.error_dict)

        js = super(VultrResponse, self).parse_body()
        if isinstance(js, dict):
            js = [js]

        json_objects.append(js)

        return (json_objects, errors)

    def _make_excp(self, error):
        """
        Convert API error to a VultrException instance
        """

        return VultrException(error['ERRORCODE'], error['ERRORMESSAGE'])

    def success(self):

        return len(self.errors) == 0


class VultrConnection(ConnectionKey):
    """
    A connection to the Vultr API
    """
    host = API_HOST
    responseCls = VultrResponse

    def add_default_params(self, params):
        """
        Returns default params such as api_key which is
        needed to perform an action.Returns a dictionary.
        Example:/v1/server/upgrade_plan?api_key=self.key
        """
        params['api_key'] = self.key

        return params

    def add_default_headers(self, headers):
        """
        Returns default headers such as content-type.
        Returns a dictionary.
        """
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Accept"] = "text/plain"

        return headers

    def set_path(self):
        self.path = '/v/'
        return self.path


class VultrException(Exception):
    """
    Error originating from the Vultr API
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "(%u) %s" % (self.code, self.message)

    def __repr__(self):
        return "VultrException code %u '%s'" % (self.code, self.message)
