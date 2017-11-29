UpCloud Driver Documentation
===============================
`UpCloud`_ is a Finnish IaaS provider offering high performance servers
from data centers based in multiple countries.

.. figure:: /_static/images/provider_logos/upcloud.png
    :align: center
    :width: 300
    :target: https://www.upcloud.com/

UpCloud currently operates globally from six (6) data centers:

* Amsterdam, Netherlands
* Chicago, USA
* Frankfurt, Germany
* Helsinki, Finland
* London, UK
* Singapore, Singapore

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``username`` - Your API access enabled users username
* ``password`` - Your API access enabled users password

Enabling API access
-------------------

To allow API access to your UpCloud account, you first need to enable the API
permissions by visiting `My Account -> User accounts`_ in your UpCloud Control
Panel. We recommend you to set up a sub-account specifically for the API usage
with its own username and password, as it allows you to assign specific permissions
for increased security.

Click **Add user** and fill in the required details, and check the
“**Allow API connections**” checkbox to enable API for the user. You can also
limit the API connections to a specific IP address or address range for additional
security. Once you are done entering the user information, hit the **Save** button
at the bottom of the page to create the new username.

.. _`UpCloud`: https://www.upcloud.com/
.. _`My Account -> User accounts`: https://my.upcloud.com/account
