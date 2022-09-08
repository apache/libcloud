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
  :ref:`Docstring conventions <docstring-conventions>` section below.
* If you are adding a new feature, make sure to add a corresponding
  documentation.

Code style guide
----------------

* We follow `The Black code style`_ and automatically enforce it for all the
  new code using black tool. You can re-format your code using black by
  running ``black`` tox target (``tox -eblack``).
* We enforce consistent import ordering using the isort library. Imports can be
  automatically re-ordered / sorted by using ``isort`` tox target (``tox -e
  isort``).
* Use 4 spaces for a tab
* Use 100 characters in a line
* Make sure edited file doesn't contain any trailing whitespace
* Make sure new code contains type annotations
* You can verify that your changes don't break any rules by running the
  following tox targets - ``lint,pylint,black`` - ``tox
  -elint,pylint,black,isort``.

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
``if foo is not None`` instead of ``if foo``.

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
conventions to which you should adhere to are described below.

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

Updating compute node sizing data
---------------------------------

Node sizing data for most providers is stored in-line as a module level
constant in the corresponding provide module.

An exception to that is AWS EC2 which sizing data is automatically generated
and scraped from AWS API as documented below.

Updating EC2 sizing and supported regions data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To update EC2 sizing data, you just need to run ``scrape-ec2-sizes`` tox target
and commit the changed files
(``libcloud/compute/constants/ec2_instance_types.py``,
``libcloud/compute/constants/ec2_region_details_complete.py``).

To add a new region update ``contrib/scrape-ec2-prices.py`` and
``contrib/scrape-ec2-sizes.py`` file (example
https://github.com/apache/libcloud/commit/762f0e5623b6f9837204ffe27d825b236c9c9970)
and then re-run corresponding tox targets as shown below:

.. sourcecode:: bash

    tox -escrape-ec2-sizes,scrape-ec2-prices

Updating compute node pricing data
----------------------------------

Pricing data for some provides is automatically scraped using
``scrape-and-publish-provider-prices`` tox target (this target required valid
AWS and Google Cloud API keys to be set for it to work).

This tox target is ran before making a new release which means that each
release includes pricing data which has been updated on the day of the release.

In addition to that, that tox target runs daily as part of our CI/CD system
and the latest version of that file is published to a public read-only S3
bucket.

For more information on how to utilize that pricing data, please see
:doc:`Pricing </compute/pricing>` page.

Contribution workflow
---------------------

1. Start a discussion on our Github repository or on the mailing list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are implementing a big feature or a change, start a discussion on the
:ref:`issue tracker <issue-tracker>` or the
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

    git checkout -b <change_name>

5. Make your changes
~~~~~~~~~~~~~~~~~~~~

6. Write tests for your changes and make sure all the tests pass
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure that all the code you have added or modified has appropriate test
coverage. Also make sure all the tests including the existing ones still pass.

Use ``libcloud.test.unittest`` as the unit testing package to ensure that
your tests work with older versions of Python.

For more information on how to write and run tests, please see
:doc:`Testing page </testing>`.

7. Commit your changes
~~~~~~~~~~~~~~~~~~~~~~

Commit your changes.

For example:

.. sourcecode:: bash

    git commit -m "Add a new compute driver for CloudStack based providers."

8. Open a pull request with your changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to https://github.com/apache/libcloud/ and open a new pull request with your
changes. Your pull request will appear at https://github.com/apache/libcloud/pulls.

9. Wait for the review
~~~~~~~~~~~~~~~~~~~~~~

Wait for your changes to be reviewed and address any outstanding comments.

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

Some examples which show how to handle those cases are described below.

Context Managers
~~~~~~~~~~~~~~~~

Context managers aren't available in Python 2.5 by default. If you want to use
them make sure to put from ``__future__ import with_statement`` on top of the
file where you use them.

Utility functions for cross-version compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find a lot of utility functions which make code easier to work with
Python 2.x and 3.x in ``libcloud.utils.py3`` module.

You can find some more information on changes which are involved in making the
code work with multiple versions on the following link -
`Lessons learned while porting Libcloud to Python 3`_

.. _`PEP8 Python Style Guide`: http://www.python.org/dev/peps/pep-0008/
.. _`Issue tracker`: https://github.com/apache/libcloud/issues
.. _`Github git repository`: https://github.com/apache/libcloud
.. _`Apache website`: https://www.apache.org/licenses/#clas
.. _`Lessons learned while porting Libcloud to Python 3`: http://www.tomaz.me/2011/12/03/lessons-learned-while-porting-libcloud-to-python-3.html
.. _`squashing commits with rebase`: http://gitready.com/advanced/2009/02/10/squashing-commits-with-rebase.html
.. _`The Black code style`: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html
