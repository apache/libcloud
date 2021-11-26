Apache Libcloud - a unified interface for the cloud
====================================================

Apache Libcloud is a Python library which hides differences between different
cloud provider APIs and allows you to manage different cloud resources
through a unified and easy to use API.


.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat
        :target: https://libcloud.readthedocs.org

.. image:: https://img.shields.io/pypi/v/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://github.com/apache/libcloud/workflows/CI/badge.svg?branch=trunk
        :target: https://github.com/apache/libcloud/actions?query=workflow%3ACI

.. image:: https://github.com/apache/libcloud/actions/workflows/integration-tests.yml/badge.svg?branch=trunk
        :target: https://github.com/apache/libcloud/actions/workflows/integration-tests.yml

.. image:: https://github.com/apache/libcloud/workflows/Publish%20pricing.json%20to%20S3%20bucket/badge.svg?branch=trunk
        :target: https://github.com/apache/libcloud/actions?query=workflow%3A%22Publish+pricing.json+to+S3+bucket%22

.. image:: https://img.shields.io/codecov/c/github/apache/libcloud/trunk.svg
        :target: https://codecov.io/github/apache/libcloud?branch=trunk

.. image:: https://img.shields.io/pypi/pyversions/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/pypi/wheel/apache-libcloud.svg
        :target: https://pypi.python.org/pypi/apache-libcloud/

.. image:: https://img.shields.io/github/license/apache/libcloud.svg
        :target: https://github.com/apache/libcloud/blob/trunk/LICENSE

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
        :target: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html

.. image:: https://img.shields.io/pypi/dm/apache-libcloud
        :target: https://pypi.org/project/apache-libcloud

.. image:: https://bestpractices.coreinfrastructure.org/projects/152/badge
        :target: https://bestpractices.coreinfrastructure.org/projects/152

.. image:: https://img.shields.io/github/contributors/apache/libcloud.svg?logo=github
        :target: https://github.com/apache/libcloud/graphs/contributors

.. image:: https://img.shields.io/github/stars/apache/libcloud.svg?logo=github
        :target: https://github.com/apache/libcloud/stargazers

.. image:: https://img.shields.io/github/forks/apache/libcloud.svg?logo=github
        :target: https://github.com/apache/libcloud/network/members

.. image:: https://repology.org/badge/tiny-repos/python:apache-libcloud.svg
        :target: https://repology.org/project/python:apache-libcloud/versions

.. image:: https://img.shields.io/twitter/follow/Libcloud.svg?style=social&label=Follow
        :target: https://twitter.com/Libcloud

:Code:          https://github.com/apache/libcloud
:License:       Apache 2.0; see LICENSE file
:Issues:        https://issues.apache.org/jira/projects/LIBCLOUD/issues
:Website:       https://libcloud.apache.org/
:Documentation: https://libcloud.readthedocs.io
:Supported Python Versions: Python >= 3.6, PyPy >= 3.6, Python 3.10 + Pyjion
                            (Python 2.7 and Python 3.4 is supported by the
                            v2.8.x release series, last version which supports
                            Python 3.5 is v3.4.0)

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

Note on Python Version Compatibility
====================================

Libcloud supports Python >= 3.6 and PyPy >= 3.6.

Support for Python 3.5 has been dropped in v3.5.0 release (in development).
Last release series which still supports Python 3.5 is v3.4.x.

Support for Python 2.7 and 3.4 has been dropped in Libcloud v3.0.0 (last
release series which still support Python 2.7 and Python 3.4 is v2.8.x).

Feedback
========

Please send feedback to the mailing list at <dev@libcloud.apache.org>,
or Github repo at <https://github.com/apache/libcloud/issues>.

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
