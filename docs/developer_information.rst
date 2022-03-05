Developer Information
=====================

Type Annotations
----------------

Python type annotations / hints for the base Libcloud compute API have been
added in v2.8.0.

The goal behind type annotations is to make developer lives easier by
introducing optional static typing for Python programs.

This allows you to catch bugs and issues which are related to variable types
earlier and faster (aka when you run ``mypy`` locally either manually or
integrated in your editor / IDE and also as part of you CI/CD build
pipeline).

An example of how to use type annotations correctly is shown below.

.. literalinclude:: /examples/compute/example_compute.py

If you reference an invalid object attribute or a method, you would
see an error similar to the one beloe when running mypy:

.. sourcecode:: python

    ...
    print(nodes[0].name)
    print(nodes[0].invalid)
    print(nodes[0].rebbot())
    print(nodes[0].reboot(foo='invalid'))
    ...

.. sourcecode:: bash

    $ mypy --no-incremental example_compute.py
    example_compute.py:41: error: "Node" has no attribute "invalid"
    example_compute.py:42: error: "Node" has no attribute "rebbot"; maybe "reboot"?
    example_compute.py:43: error: Unexpected keyword argument "foo" for "reboot" of "Node"

If you are using driver methods which are not part of the Libcloud standard
API, you need to use ``cast()`` method as shown below to cast the driver class
to the correct type. If you don't do that, ``mypy`` will only be aware of the
methods which are part of the Libcloud base compute API (aka
``BaseNodeDriver`` class).

This is needed because of how Libcloud utilizes meta programming for the
``get_driver()`` and related methods (there is no other way without writing
a mypy plugin to achieve that).

.. _mailing-lists:

Mailing Lists
-------------

All of the communication about Libcloud development happens on our mailing
lists.

* `announce@libcloud.apache.org`_ - Moderated and low volume mailing list which
  is only used for distributing important project announcements and updates.
  (`announce-archive <https://mail-archives.apache.org/mod_mbox/libcloud-announce/>`_)
* `users@libcloud.apache.org`_ - Mailing list for general talk about Libcloud
  and other off-topic things
  (`users-archive <https://mail-archives.apache.org/mod_mbox/libcloud-users/>`_)
* `dev@libcloud.apache.org`_ - General mailing list for developers
  (`dev-archive <https://mail-archives.apache.org/mod_mbox/libcloud-dev/>`_)
* `notifications@libcloud.apache.org`_ - Commits messages and other automatically
  generated notifications go to this mailing list.
  Keep in mind that unlike the others, this mailing list is fairly noisy.
  (`notifications-archive <https://mail-archives.apache.org/mod_mbox/libcloud-notifications/>`_, `commits-archive <https://mail-archives.apache.org/mod_mbox/libcloud-commits/>`_)

Archive of old incubator mailing lists:

* `incubator-libcloud`_
* `incubator-libcloud-commits`_

.. _irc:

IRC
---

* #libcloud on Libera.chat (https://libera.chat)

.. _issue-tracker:

Issue Tracker
-------------

For bug and issue tracking we use Github issues located at
https://github.com/apache/libcloud/issues.

Testing
-------

For information how to run the tests and how to generate the test coverage
report, please see the :doc:`Testing page </testing>`.

.. _ci-cd:

Continuous Integration
----------------------

For continuous integration we use Travis-CI. You can find build reports on the
following links:

* https://travis-ci.org/apache/libcloud

Travis-CI builder is also integrated with Github which means that if you open a
pull request there, Travis-CI will automatically build it.

If you want to validate the build before raising the PR, Travis-CI can be enabled for personal
accounts and branches separately.

.. _code-coverage:

Test Coverage
-------------

Test coverage report is automatically generated after every push and can be
found at https://codecov.io/github/apache/libcloud?branch=trunk.

.. _`announce@libcloud.apache.org`: mailto:announce-subscribe@libcloud.apache.org
.. _`users@libcloud.apache.org`: mailto:users-subscribe@libcloud.apache.org
.. _`dev@libcloud.apache.org`: mailto:dev-subscribe@libcloud.apache.org
.. _`notifications@libcloud.apache.org`: mailto:notifications-subscribe@libcloud.apache.org
.. _`incubator-libcloud`: http://mail-archives.apache.org/mod_mbox/incubator-libcloud/
.. _`incubator-libcloud-commits`: http://mail-archives.apache.org/mod_mbox/incubator-libcloud-commits/
