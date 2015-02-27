Development
===========

This page describes Libcloud development process and contains general
guidelines and information on how to contribute to the project.

Contributing
------------

We welcome contributions of any kind (ideas, code, tests, documentation,
examples, ...).

If you need help or get stuck at any point during this process, stop by on our
IRC channel (:ref:`#libcloud on freenode <irc>`) and we will do our best to
assist you.

Getting started with contributing to Libcloud
---------------------------------------------

General contribution guidelines
-------------------------------

* Any non-trivial change must contain tests. For more information, refer to the
  :doc:`Testing page </testing>`.
* All the functions and methods must contain Sphinx docstrings which are used
  to generate the API documentation. For more information, refer to the
  :ref:`Docstring conventions <docstring-conventions>` section bellow.
* If you are adding a new feature, make sure to add a corresponding
  documentation.

Code style guide
----------------

* We follow `PEP8 Python Style Guide`_
* Use 4 spaces for a tab
* Use 79 characters in a line
* Make sure edited file doesn't contain any trailing whitespace
* You can verify that your modifications don't break any rules by running the
  ``flake8`` script - e.g. ``flake8 libcloud/edited_file.py.`` or
  ``tox -e lint``.
  Second command fill run flake8 on all the files in the repository.

And most importantly, follow the existing style in the file you are editing and
**be consistent**.

Git pre-commit hook
-------------------

To make complying with our style guide easier, we provide a git pre-commit hook
which automatically checks modified Python files for violations of our style
guide.

You can install it by running following command in the root of the repository
checkout:

.. sourcecode:: bash

    ln -s contrib/pre-commit.sh .git/hooks/pre-commit

After you have installed this hook it will automatically check modified Python
files for violations before a commit. If a violation is found, commit will be
aborted.

.. _code-conventions:

Code conventions
----------------

This section describes some general code conventions you should follow when
writing a Libcloud code.

1. Import ordering
~~~~~~~~~~~~~~~~~~

Organize the imports in the following order:

1. Standard library imports
2. Third-party library imports
3. Local library (Libcloud) imports

Each section should be separated with a blank line. For example:

.. sourcecode:: python

    import sys
    import base64

    import paramiko

    from libcloud.compute.base import Node, NodeDriver
    from libcloud.compute.providers import Provider

2. Function and method ordering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Functions in a module and methods on a class should be organized in the
following order:

1. "Public" functions / methods
2. "Private" functions / methods (methods prefixed with an underscore)
3. "Internal" methods (methods prefixed and suffixed with a double underscore)

For example:

.. sourcecode:: python

    class Unicorn(object):
        def __init__(self, name='fluffy'):
            self._name = name

        def make_a_rainbow(self):
            pass

        def _get_rainbow_colors(self):
            pass

        def __eq__(self, other):
            return self.name == other.name

Methods on a driver class should be organized in the following order:

1. Methods which are part of the standard API
2. Extension methods
3. "Private" methods (methods prefixed with an underscore)
4. "Internal" methods (methods prefixed and suffixed with a double underscore)

Methods which perform a similar functionality should be grouped together and
defined one after another.

For example:

.. sourcecode:: python

    class MyDriver(object):
        def __init__(self):
            pass

        def list_nodes(self):
            pass

        def list_images(self):
            pass

        def create_node(self):
            pass

        def reboot_node(self):
            pass

        def ex_create_image(self):
            pass

        def _to_nodes(self):
            pass

        def _to_node(self):
            pass

        def _to_images(self):
            pass

        def _to_image(self):
            pass

Methods should be ordered this way for the consistency reasons and to make
reading and following the generated API documentation easier.

3. Prefer keyword over regular arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For better readability and understanding of the code, prefer keyword over
regular arguments.

Good:

.. sourcecode:: python

    some_method(public_ips=public_ips, private_ips=private_ips)

Bad:

.. sourcecode:: python

    some_method(public_ips, private_ips)

4. Don't abuse \*\*kwargs
~~~~~~~~~~~~~~~~~~~~~~~~~

You should always explicitly declare arguments in a function or a method
signature and only use ``**kwargs`` and ``*args`` respectively when there is a
valid use case for it.

Using ``**kwargs`` in many contexts is against Python's "explicit is better
than implicit" mantra and makes it for a bad and a confusing API. On top of
that, it makes many useful things such as programmatic API introspection hard
or impossible.

A use case when it might be valid to use ``**kwargs`` is a decorator.

Good:

.. sourcecode:: python

    def my_method(self, name, description=None, public_ips=None):
        pass

Bad (please avoid):

.. sourcecode:: python

    def my_method(self, name, **kwargs):
        description = kwargs.get('description', None)
        public_ips = kwargs.get('public_ips', None)

5. When returning a dictionary, document its structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dynamic nature of Python can be very nice and useful, but if (ab)use it in a
wrong way it can also make it hard for the API consumer to understand what is
going on and what kind of values are being returned.

If you have a function or a method which returns a dictionary, make sure to
explicitly document in the docstring which keys the returned dictionary
contains.

6. Prefer to use "is not None" when checking if a variable is provided or defined
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When checking if a variable is provided or defined, prefer to use
``is foo is not None`` instead of ``if foo``.

If you use ``if foo`` approach, it's easy to make a mistake when a valid value
can also be falsy (e.g. a number ``0``).

For example:

.. sourcecode:: python

    class SomeClass(object):
        def some_method(self, domain=None):
            params = {}

            if domain is not None:
                params['Domain'] = domain

.. _docstring-conventions:

Docstring conventions
---------------------

For documenting the API we we use Sphinx and reStructuredText syntax. Docstring
conventions to which you should adhere to are described bellow.

* Docstrings should always be used to describe the purpose of methods,
  functions, classes, and modules.
* Method docstring should describe all the normal and keyword arguments. You
  should describe all the available arguments even if you use ``*args`` and
  ``**kwargs``.
* All parameters must be documented using ``:param p:`` or ``:keyword p:``
  and ``:type p:`` annotation.
* ``:param p: ...`` -  A description of the parameter ``p`` for a function
  or method.
* ``:keyword p: ...`` - A description of the keyword parameter ``p``.
* ``:type p: ...`` The expected type of the parameter ``p``.
* Return values must be documented using ``:return:`` and ``:rtype``
  annotation.
* ``:return: ...`` A description of return value for a function or method.
* ``:rtype: ...`` The type of the return value for a function or method.
* Required keyword arguments must contain ``(required)`` notation in
  description. For example: ``:keyword image:  OS Image to boot on node. (required)``
*  Multiple types are separated with ``or``
   For example: ``:type auth: :class:`.NodeAuthSSHKey` or :class:`.NodeAuthPassword```
* For a description of the container types use the following notation:
  ``<container_type> of <objects_type>``. For example:
  ``:rtype: `list` of :class:`Node```

For more information and examples, please refer to the following links:

* Sphinx Documentation - http://sphinx-doc.org/markup/desc.html#info-field-lists
* Example Libcloud module with documentation - https://github.com/apache/libcloud/blob/trunk/libcloud/compute/base.py

Contribution workflow
---------------------

1. Start a discussion on the mailing list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are implementing a big feature or a change, start a discussion on the
:ref:`mailing list <mailing-lists>` first.

2. Open a new issue on our issue tracker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to our `issue tracker`_ and open a new issue for your changes there. This
issue will be used as an umbrella place for your changes. As such, it will be
used to track progress and discuss implementation details.

3. Fork our Github repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fork our `Github git repository`_. Your fork will be used to hold your changes.

4. Create a new branch for your changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For example:

.. sourcecode:: bash

    git checkout -b <jira_issue_id>_<change_name>

5. Make your changes
~~~~~~~~~~~~~~~~~~~~

6. Write tests for your changes and make sure all the tests pass
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure that all the code you have added or modified has appropriate test
coverage. Also make sure all the tests including the existing ones still pass.

For more information on how to write and run tests, please see
:doc:`Testing page </testing>`.

7. Commit your changes
~~~~~~~~~~~~~~~~~~~~~~

Make a single commit for your changes. If a corresponding JIRA ticket exists,
make sure the commit message contains the ticket number.

For example:

.. sourcecode:: bash

    git commit -a -m "[LIBCLOUD-123] Add a new compute driver for CloudStack based providers."

8. Open a pull request with your changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to https://github.com/apache/libcloud/ and open a new pull request with your
changes. Your pull request will appear at https://github.com/apache/libcloud/pulls.

Make sure the pull request name is prefixed with a JIRA ticket number, e.g.
``[LIBCLOUD-436] Improvements to DigitalOcean compute driver`` and that the
pull request description contains link to the JIRA ticket.

9. Wait for the review
~~~~~~~~~~~~~~~~~~~~~~

Wait for your changes to be reviewed and address any outstanding comments.

10. Squash the commits and generate the patch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the changes has been reviewed, all the outstanding issues have been
addressed and the pull request has been +1'ed, close the pull request, squash
the commits (if necessary) and generate a patch.

.. sourcecode:: bash

    git format-patch --stdout trunk > patch_name.patch

Make sure to use ``git format-patch`` and not ``git diff`` so we can preserve
the commit authorship.

Note #1: Before you generate the patch and squash the commits, make sure to
synchronize your branch with the latest trunk (run ``git pull upstream trunk``
in your branch), otherwise we might have problems applying it cleanly.

Note #2: If you have never used rebase and squashed the commits before, you can
find instructions on how to do that in the following guide:
`squashing commits with rebase`_.

11. Attach a final patch with your changes to the corresponding JIRA ticket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Attach the generated patch to the JIRA issue you have created earlier.

Note about Github
~~~~~~~~~~~~~~~~~

Github repository is a read-only mirror of the official Apache git repository
(``https://git-wip-us.apache.org/repos/asf/libcloud.git``). This mirror script
runs only a couple of times per day which means this mirror can be slightly out
of date.

You are advised to add a separate remote for the official upstream repository:

.. sourcecode:: bash

    git remote add upstream https://git-wip-us.apache.org/repos/asf/libcloud.git

Github read-only mirror is used only for pull requests and code review. Once a
pull request has been reviewed, all the comments have been addresses and it's
ready to be merged, user who submitted the pull request must close the pull
request, create a patch and attach it to the original JIRA ticket.

Syncing your git(hub) repository with an official upstream git repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to synchronize your git clone / Github fork with
an official upstream repository.

It's important that your repository is in-sync with the upstream one when you
start working on a new branch and before you generate a final patch. If the
repository is not in-sync, generated patch will be out of sync and we won't be
able to cleanly merge it into trunk.

To synchronize it, follow the steps bellow in your git clone:

1. Add upstream remote if you haven't added it yet

.. sourcecode:: bash

    git remote add upstream https://git-wip-us.apache.org/repos/asf/libcloud.git

2. Synchronize your ``trunk`` branch with an upstream one

.. sourcecode:: bash

    git checkout trunk
    git pull upstream trunk

3. Create a branch for your changes and start working on it

.. sourcecode:: bash

    git checkout -b my_new_branch

4. Before generating a final patch which is to be attached to the JIRA ticket,
   make sure your repository and branch is still in-sync

.. sourcecode:: bash

    git pull upstream trunk

5. Generate a patch which can be attached to the JIRA ticket

.. sourcecode:: bash

    git format-patch --stdout remotes/upstream/trunk > patch_name.patch

Contributing Bigger Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are contributing a bigger change (e.g. large new feature or a new
provider driver) you need to have signed Apache Individual Contributor
License Agreement (ICLA) in order to have your patch accepted.

You can find more information on how to sign and file an ICLA on the
`Apache website`_.

When filling the form, leave field ``preferred Apache id(s)`` empty and in
the ``notify project`` field, enter ``Libcloud``.

Supporting Multiple Python Versions
-----------------------------------

Libcloud supports a variety of Python versions so your code also needs to work
with all the supported versions. This means that in some cases you will need to
include extra code to make sure it works in all the supported versions.

Some examples which show how to handle those cases are described bellow.

Context Managers
~~~~~~~~~~~~~~~~

Context managers aren't available in Python 2.5 by default. If you want to use
them make sure to put from ``__future__ import with_statement`` on top of the
file where you use them.

Exception Handling
~~~~~~~~~~~~~~~~~~

There is no unified way to handle exceptions and extract the exception object
in Python 2.5 and Python 3.x. This means you need to use a
``sys.exc_info()[1]`` approach to extract the raised exception object.

For example:

.. sourcecode:: python

    try:
        some code
    except Exception:
        e = sys.exc_info()[1]
        print e

Utility functions for cross-version compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find a lot of utility functions which make code easier to work with
Python 2.x and 3.x in ``libcloud.utils.py3`` module.

You can find some more information on changes which are involved in making the
code work with multiple versions on the following link -
`Lessons learned while porting Libcloud to Python 3`_

.. _`PEP8 Python Style Guide`: http://www.python.org/dev/peps/pep-0008/
.. _`Issue tracker`: https://issues.apache.org/jira/browse/LIBCLOUD
.. _`Github git repository`: https://github.com/apache/libcloud
.. _`Apache website`: https://www.apache.org/licenses/#clas
.. _`Lessons learned while porting Libcloud to Python 3`: http://www.tomaz.me/2011/12/03/lessons-learned-while-porting-libcloud-to-python-3.html
.. _`squashing commits with rebase`: http://gitready.com/advanced/2009/02/10/squashing-commits-with-rebase.html
