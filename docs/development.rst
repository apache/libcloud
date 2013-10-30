Development
===========

Contributing
------------

We welcome contributions of any kind (ideas, code, tests, documentation,
examples, ...).

This page explains how you can contribute to the Libcloud project. If you get
stuck at any point during this process, stop by on our IRC channel (#libcloud
on freenode) and we will do our best to assist you.

Style guide
-----------

* We follow `PEP8 Python Style Guide`_
* Use 4 spaces for a tab
* Use 79 characters in a line
* Make sure edited file doesn't contain any trailing whitespace
* You can verify that your modifications don't break any rules by running the
  ``flake8`` script - e.g. ``flake8 libcloud/edited_file.py.`` or
  ``tox -e lint``.
  Second command fill run flake8 on all the files in the repository.

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

General guidelines
------------------

* Any non-trivial change must contain tests
* All the functions and methods must contain Sphinx docstrings which are used
  to generate API documentation. You can find a lot of examples of docstrings
  in the existing code e.g. - ``libcloud/compute/base.py``
* If you are adding a new feature, make sure to add corresponding documentation

Contribution workflow
---------------------

1. If you are implementing a big feature or a change, start a discussion on the
   mailing list first.
2. Open a new issue on our `issue tracker`_ (JIRA)
3. Fork libcloud `Github git repository`_ and make your changes
4. Create a new branch for your changes:
   ``git checkout -b <jira_issue_id>_<change_name>``
5. Make your changes
6. Make a single commit for your changes and if a corresponding JIRA
   ticket exists, make sure the commit message contains the ticket number.
   For example: ``git commit -a -m "Issue LIBCLOUD-123: Add a new compute driver for CloudStack based providers."``
7. Write tests for your modifications and make sure that all the tests pass.
   For more information about running the tests refer to the Testing page.
8. Open a pull request with your changes. Your pull request will appear at
   https://github.com/apache/libcloud/pulls
9. Wait for the code to be reviewed and address any outstanding comments.
10. Once the code has been reviewed, all the outstanding issues have been
    addressed and the pull request has been +1'ed, close the pull request,
    generate a patch and attach it to the JIRA issue you have created earlier:
    ``git format-patch --stdout trunk > patch_name.patch``

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
provider driver) you need to have have signed Apache Individual Contributor
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
