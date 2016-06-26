Apache Libcloud - a unified interface into the cloud
====================================================

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat
    :target: https://libcloud.readthedocs.org

.. image:: https://img.shields.io/pypi/v/apache-libcloud.svg
    :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/pypi/dm/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/travis/apache/libcloud/trunk.svg
        :target: http://travis-ci.org/apache/libcloud

.. image:: https://img.shields.io/pypi/pyversions/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/pypi/wheel/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/github/license/apache/libcloud.svg
        :target: https://github.com/apache/libcloud/blob/trunk/LICENSE

.. image:: https://img.shields.io/irc/%23libcloud.png
        :target: http://webchat.freenode.net/?channels=libcloud

.. image:: https://bestpractices.coreinfrastructure.org/projects/152/badge
        :target: https://bestpractices.coreinfrastructure.org/projects/152

.. image:: https://coveralls.io/repos/github/apache/libcloud/badge.svg?branch=trunk
        :target: https://coveralls.io/github/apache/libcloud?branch=trunk

Apache Libcloud is a Python library which hides differences between different
cloud provider APIs and allows you to manage different cloud resources
through a unified and easy to use API.

Resources you can manage with Libcloud are divided into the following categories:

* **Compute** - Cloud Servers and Block Storage - services such as Amazon EC2 and Rackspace
  Cloud Servers (``libcloud.compute.*``)
* **Storage** - Cloud Object Storage and CDN  - services such as Amazon S3 and Rackspace
  CloudFiles (``libcloud.storage.*``)
* **Load Balancers** - Load Balancers as a Service, LBaaS (``libcloud.loadbalancer.*``)
* **DNS** - DNS as a Service, DNSaaS (``libcloud.dns.*``)
* **Container** - Container virtualization services (``libcloud.container.*``)


Apache Libcloud is an Apache project, see <http://libcloud.apache.org> for
more information.

Documentation
=============

Documentation can be found at <https://libcloud.readthedocs.org>.

Feedback
========

Please send feedback to the mailing list at <dev@libcloud.apache.org>,
or the JIRA at <https://issues.apache.org/jira/browse/LIBCLOUD>.

Contributing
============

For information on how to contribute, please see the Contributing
chapter in our documentation
<https://libcloud.readthedocs.org/en/latest/development.html#contributing>

License
=======

Apache Libcloud is licensed under the Apache 2.0 license. For more information, please see LICENSE_ and NOTICE_  file.

.. _LICENSE: https://github.com/apache/libcloud/blob/trunk/LICENSE
.. _NOTICE: https://github.com/apache/libcloud/blob/trunk/NOTICE
