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

Apache Libcloud 是一个Python库，它隐蔽了不同云资源API层的差异并允许您通过统一且易于使用的API来管理不同的云资源。

您可以使用Libcloud管理的资源分为以下类别：

* **计算** - 云服务器和块存储 - 服务例子： Amazon EC2 和 Rackspace
  Cloud Servers (``libcloud.compute.*``)
* **存储** - 云对象存储 and 内容交付网络(CDN-Content Delivery Network ）  - 服务例子： Amazon S3 和 Rackspace
  CloudFiles (``libcloud.storage.*``)
* **负载平衡器** - 作为服务的负载平衡器, LBaaS (``libcloud.loadbalancer.*``)
* **域名服务器 ( DNS - Domain name server )** - 作为服务的域名服务器, DNSaaS (``libcloud.dns.*``)
* **容器** - 虚拟化服务容器 (``libcloud.container.*``)


Apache Libcloud 是一个 Apache 的计划, 往 <http://libcloud.apache.org> 看以获得更多资料

文档
==

文档可以在 <https://libcloud.readthedocs.org> 找得到.

反馈
==

请将反馈发送到邮件列表 <dev@libcloud.apache.org>,
或者到 JIRA 在 <https://issues.apache.org/jira/browse/LIBCLOUD>.

贡献
==

有关如何贡献的信息，请参阅贡献在我们的文档中的贡献章节 <https://libcloud.readthedocs.org/en/latest/development.html#contributing>

执照
==

Apache Libcloud是被Apache 2.0许可证授权的。 更多有关详情，请参阅 LICENSE_ 和 NOTICE_ 文件。

.. _LICENSE: https://github.com/apache/libcloud/blob/trunk/LICENSE
.. _NOTICE: https://github.com/apache/libcloud/blob/trunk/NOTICE
