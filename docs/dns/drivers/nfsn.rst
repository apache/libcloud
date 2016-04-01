NFSN DNS Driver Documentation
===================================

`NFSN`_, Inc. is a U.S. company that provides web hosting and domain name
server services.

Instantiating the driver
------------------------

To instantiate the driver you need to pass the account name and API key to the
driver constructor as shown below. Obtain your API key from NFSN by submitting
a secure support request via the `control panel`_.

.. literalinclude:: /examples/dns/nfsn/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.nfsn.NFSNDNSDriver
    :members:
    :inherited-members:

.. _`NFSN`: https://www.nearlyfreespeech.net/
.. _`control panel`: https://members.nearlyfreespeech.net/
