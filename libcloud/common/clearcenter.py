import json
import socket

from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib
from libcloud.compute.base import (Node, NodeDriver, NodeState,
                                   KeyPair, NodeLocation, NodeImage)
from libcloud.common.types import InvalidCredsError
from libcloud.common.base import JsonResponse
from libcloud.common.base import ConnectionKey



class ClearCenterResponse(JsonResponse):
    """
    ClearCenter response class
    """

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        :rtype: ``bool``
        :return: ``True`` or ``False``
        """

        # ClearCenter returns 200 even on a false apikey
        body = self.parse_body()
        if "Authentication Required" in body:
            raise InvalidCredsError("Provided apikey not valid")

        return self.status in [httplib.OK, httplib.CREATED, httplib.NO_CONTENT]

    def parse_error(self):

        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            error = body.get('errors', {}).get('base')
            if error and isinstance(error, list):
                error = error[0]
            raise InvalidCredsError(error)
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body['message'], self.status)
            else:
                error = body
            raise Exception(error)


class ClearCenterConnection(ConnectionKey):
    """
    ClearCenter connection class
    """

    responseCls = ClearCenterResponse

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``apikey`` to the request.
        """

        headers['Authorization'] = 'Bearer %s' % (self.key)
        headers['Content-Type'] = 'application/json'
        return headers

    # def add_default_params(self, params):
    #     """
    #     Add the limit param to 500 in order not to paginate
    #     """
    #     params['limit'] = "500"
    #     return params
