from base64 import b64encode
from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib
from libcloud.common.base import ConnectionUserAndKey, JsonResponse


class OnAppResponse(JsonResponse):
    """
    OnApp response class
    """

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        :rtype: ``bool``
        :return: ``True`` or ``False``
        """
        return self.status in [httplib.OK, httplib.CREATED, httplib.NO_CONTENT]


class OnAppConnection(ConnectionUserAndKey):
    """
    OnApp connection class
    """

    responseCls = OnAppResponse

    def __init__(self, user_id, key, secure=True, host=None):
        """
        :param user_id: username to authorize at onapp
        :type  user_id: ``str``

        :param key: password to authorize at onapp
        :type  key: ``str``

        :param secure: use https or not
        :type  secure: ``bool``

        :param host: host
        :type  host: ``str``

        :rtype: :class:`OnAppConnection`
        """
        super(OnAppConnection, self).__init__(user_id, key, secure=secure,
                                              host=host)

    def add_default_headers(self, headers):
        """
        Add Basic Authentication header to all the requests.
        It injects the "Authorization: Basic Base64String===" header
        in each request
        :type  headers: ``dict``
        :param headers: Default input headers
        :rtype:         ``dict``
        :return:        Default input headers with the "Authorization"
                        header
        """
        b64string = b("%s:%s" % (self.user_id, self.key))
        encoded = b64encode(b64string).decode("utf-8")

        headers["Authorization"] = "Basic " + encoded
        return headers
