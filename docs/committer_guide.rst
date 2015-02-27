Committer Guide
===============

New committer guidelines
------------------------

.. note::

    This section outlines steps which need to be completed by new team members and
    is indented for people who have been voted to join Libcloud project as a
    committer and / or PMC member. It also assumes you have already filled
    your ICLA and your Apache account has been created.

First congratulations and welcome to the team!

1. Subscribe to the public mailing lists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you haven't yet, subscribe to {dev,users,commits}@apache.libcloud.org
mailing lists. Committs mailing list is especially important because all of
the JIRA notification, Gihub Pull Request notifications and build notifications
are sent there.

2. Subscribe to the private mailing list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Subscribe to private@libcloud.apache.org by sending an email to
private-subscribe@libcloud.apache.org. Keep in mind that this list is private
and your subscription needs to be approved by a moderator.

3. Create PyPi account
~~~~~~~~~~~~~~~~~~~~~~

Creating a PyPi account by going to
https://pypi.python.org/pypi?%3Aaction=register_form and send an email to
private@libcloud.apache.org requesting to be added as a maintainer to
`apache-libcloud <https://pypi.python.org/pypi/apache-libcloud/>`_ package.
Make sure to select a strong and unique password (``pwgen -s 48 1`` is your
friend).

After you have registered go to
"`Your details <https://pypi.python.org/pypi?%3Aaction=user_form>`_" page and
populate `PGP Key ID` field with your PGP key ID.

Applying a patch
----------------

When applying a third-party patch created using ``git format-patch`` command,
use the following command:

.. sourcecode:: bash

    git am --signoff < patch_name.patch

``--signoff`` argument signs the patch and lets others know that you have
reviewed and merged a patch.

If you are merging a patch from the Github pull request, don't forget to
update the commit message during rebase (or use git commit --amend if the
rebase was not necessary) to include the "Closes #prnumber" message. This way,
the corresponding Github pull request will get automatically closed once the
Github mirror is updated.

For example::

    ...
    Original message
    ...

    Closes #prnumber

After the patch has been applied, make sure to update ``CHANGES`` file.

Making a release (for release managers)
---------------------------------------

This section contains information a release manager should follow when
preparing a release.

1. Pre-release check list
~~~~~~~~~~~~~~~~~~~~~~~~~

* Make sure tests pass on all the supported Python versions (``tox``)
* Make sure ``CHANGES`` file is up to date
* Make sure ``__version__`` string in ``libcloud/__init__.py`` is up to date
* Remove the ``tox`` directory with ``rm -rf .tox``
* Remove the _secrets_ file with ``rm test/secrets.py``

2. Update JIRA
~~~~~~~~~~~~~~

* Create a new JIRA version for the release in question (if one doesn't exist
  yet)
* Close all the corresponding JIRA tickets and set ``Fix Version/s`` field
  to the current version
* Release the JIRA version

3. Creating release artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We have a script that runs the required setup.py commands and then hashes
and signs the files. You will need the latest version of ``pip`` and the ``wheel``
package. To run it:

.. sourcecode:: bash

    cd dist
    ./release.sh -u <yourusername>@apache.org

``-u`` argument will be used to find a key with a matching email address in
your local GPG database.

This should result in a set of
``apache-libcloud-${VERSION}.{tar.bz2,tar.gz,zip}{,asc,md5,sha1}`` files that
are suitable to be uploaded for a release.

Copy the artifacts in another directory, unpack one of them and test it with ``tox``.

4. Tagging a release
~~~~~~~~~~~~~~~~~~~~

Tag the tentative release with a ``-tentative`` postfix.

.. sourcecode:: bash

    git tag <version> <commit hash>

For example:

.. sourcecode:: bash

    git tag v0.15.0-tentative 105b9610835f99704996d861d613c5a9a8b3f8b1

5. Upload the release artifacts and start a [VOTE] thread
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Upload all release artifacts including the ``whl`` files to your people.apache.org
space. Then start a [VOTE] thread on the dev@libcloud.apache.org mailing list.

Once the vote has passed tag the release with a new tag, removing the ``-tentative`` postfix.
Upload the release artifacts to Apache servers and Pypi.

6. Uploading release artifacts to Apache servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add release artifacts to the dist SVN repository at
  https://dist.apache.org/repos/dist/release/libcloud/

  It may take up to a day for the artifacts to be available on all the
  Apache mirrors, but they should be instantly available at
  http://www.apache.org/dist/libcloud/.

* If there is more than one old release in the repository, delete rest of the
  old release and only leave current and previous release there. Old releases
  are automatically archived and available at
  https://dist.apache.org/repos/dist/release/libcloud/.

7. Publishing package to PyPi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For consistency and security reasons packages are always uploaded to PyPi
manually using the web interface and not using the setup.py upload
command.**

* Run ``python setup.py register`` command. This will register a new
  version on PyPi, but it won't upload the actual release artifacts.

* Go to the `PyPi release management page`_, find a new release and click on
  "files" link.

* Once you are there, upload all the release artifacts (.tar.bz2, .tar.gz,
  .zip, and .whl). For ``File Type`` select ``Source`` (except for ``.whl``
  file where you should select ``Python Wheel``) and for ``Python Version``
  select ``Any (ie. pure Python)``. Make sure to also select and upload a PGP
  signature for each file (``PGP signature (.asc)`` field).

Once all the files have been uploaded, the page should look similar to the
screenshot below.

.. image:: _static/images/pypi_files_page.png
   :width: 700px
   :align: center

8. Verifying the release artifact check sums
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To verify that nothing went wrong doing the release process, run the
``./dist/verify_checksums.sh`` script.

This script downloads the release artifacts from the Apache and PyPi server and
makes sure that the MD5 check sums of the both files match.

Usage:

.. sourcecode:: bash

    ./dist/verify_checksums.sh <version>

For example

.. sourcecode:: bash

    ./dist/verify_checksums.sh apache-libcloud-0.13.2

9. Updating doap_libcloud.rdf file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add information about the new release to the ``doap_libcloud.rdf`` file in the
root of the main code repository.

10. Updating website
~~~~~~~~~~~~~~~~~~~~

Check out the website using SVN: ``svn co https://svn.apache.org/repos/asf/libcloud/site/trunk``

* Upate the front page (``source/index.html`` file)
* Update "Downloads" page (``source/downloads.md`` file)
* Add a blog entry in the ``_posts`` directory.

Build the site locally and make sure everything is correct. Check the ``README.md`` file.

11. Sending announcements
~~~~~~~~~~~~~~~~~~~~~~~~~

* Send a release announcement to {dev,users}@libcloud.apache.org. If it's a
  major release also send it to announce@apache.org.
* Send a release announcement to Twitter and Google+

Note: If the release fixes a security vulnerability, you should also send
information about a vulnerability to the following full disclosure mailing
lists:

* full-disclosure@lists.grok.org.uk
* bugtraq@securityfocus.com

The email you send should also be signed using your GPG key. You can find
an example of such announcement on the `following url <http://seclists.org/fulldisclosure/2014/Jan/11>`_.

If needed, use Apache URL shortening service - http://s.apache.org/

Mailing list email templates
----------------------------

This section includes email templates which can be used when sending out
official communication to the mailing lists.

Release voting thread template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This template should be used when starting a voting thread for a new release.

Subject::

    [VOTE] Release Apache Libcloud <version>

Body::

    This is a voting thread for Libcloud <version>.

    <short description and highlights of this release>

    Full changelog can be found at <link to the CHANGES file for this release>.

    Release artifacts can be found at <link to your Apache space where a release
    artifacts can be found>.

    KEYS file can found at https://dist.apache.org/repos/dist/release/libcloud/KEYS

    Please test the release and post your votes.

    +/- 1
    [  ]  Release Apache Libcloud <version>

    Vote will be opened until <date, it should be at minimum today + 3 days> (or longer, if needed).

    Thanks,
    <name>

For example:

Subject::

    [VOTE] Release Apache Libcloud 0.13.2

Body::

    This is a voting thread for Libcloud 0.13.2.

    This is another primarily a bug-fix release. Previous release included a fix for the Content-Length bug which didn't fully fix the original issue. It missed out "raw" requests which are fixed in this release (LIBCLOUD-396).

    This bug could manifest itself while uploading a file with some of the storage providers.

    Besides this bug fix, it includes a couple of other smaller bug fixes and changes. Full change log
    can be found at https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=b7747f777afdeb63bcacf496d1d034f1b3287c31;hb=c4b3daae946049652a500a8515929b4cbf14a6b4

    Release artifacts can be found at http://people.apache.org/~tomaz/libcloud/.

    Please test the release and post your votes.

    +/- 1
    [  ]  Release Apache Libcloud 0.13.2

    Vote will be opened until September 18th, 2013 (or longer, if needed).

    Thanks,
    Tomaz

Release announcement
~~~~~~~~~~~~~~~~~~~~

This template should be used when sending out a release announcement.

Subject::

    [ANNOUNCE] Apache Libcloud 0.13.1 release

Body::

    Libcloud is a Python library that abstracts away the differences among
    multiple cloud provider APIs. It allows users to manage cloud services
    (servers, storage, loadbalancers, DNS) offered by many different providers
    through a single, unified and easy to use API.

    We are pleased to announce the release of Libcloud <version>!

    <short description of the release which should include release highlights>

    Full change log can be found at <link to CHANGES file for this release>

    Download

    Libcloud <version> can be downloaded from http://libcloud.apache.org/downloads.html
    or installed using pip:

    pip install apache-libcloud

    Upgrading

    If you have installed Libcloud using pip you can also use it to upgrade it:

    pip install --upgrade apache-libcloud

    Upgrade notes

    A page which describes backward incompatible or semi-incompatible
    changes and how to preserve the old behavior when this is possible
    can be found at http://libcloud.apache.org/upgrade-notes.html.

    Documentation

    API documentation can be found at http://libcloud.apache.org/apidocs/<version>/.

    We also have a new Sphinx documentation which can be found at https://libcloud.apache.org/docs/.

    Bugs / Issues

    If you find any bug or issue, please report it on our issue tracker
    <https://issues.apache.org/jira/browse/LIBCLOUD>.
    Don't forget to attach an example and / or test which reproduces your problem.

    Thanks

    Thanks to everyone who contributed and made this release possible! Full list of
    people who contributed to this release can be found in the CHANGES file
    <link to the changes file for this release>.

For example:

Subject::

    [ANNOUNCE] Apache Libcloud 0.13.1 release

Body::

    Libcloud is a Python library that abstracts away the differences among
    multiple cloud provider APIs. It allows users to manage cloud services
    (servers, storage, loadbalancers, DNS) offered by many different providers
    through a single, unified and easy to use API.

    We are pleased to announce the release of Libcloud 0.13.1!

    This is a bug-fix only release. Among some smaller bugs it also fixes
    Content-Length regression which broke create and update operations in
    the Bluebox Compute and Azure Storage driver (LIBCLOUD-362, LIBCLOUD-3901).

    Full change log can be found at <https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=ca90c84e296ca82e2206eb86ed7364c588aad503;hb=602b6a7a27dca6990a38eb887e1d6615826387d5>

    Download

    Libcloud 0.13.1 can be downloaded from http://libcloud.apache.org/downloads.html
    or installed using pip:

    pip install apache-libcloud

    Upgrading

    If you have installed Libcloud using pip you can also use it to upgrade it:

    pip install --upgrade apache-libcloud

    Upgrade notes

    A page which describes backward incompatible or semi-incompatible
    changes and how to preserve the old behavior when this is possible
    can be found at http://libcloud.apache.org/upgrade-notes.html.

    Documentation

    API documentation can be found at http://libcloud.apache.org/apidocs/0.13.1/.

    We also have a new Sphinx documentation which can be found at https://libcloud.apache.org/docs/.
    Keep in mind though, that this documentation reflects state in trunk which
    includes some backward incompatible changes which aren't present in 0.13.1.
    All the examples in the documentation which only work with trunk are clearly marked with a note.

    Bugs / Issues

    If you find any bug or issue, please report it on our issue tracker
    <https://issues.apache.org/jira/browse/LIBCLOUD>.
    Don't forget to attach an example and / or test which reproduces your problem.

    Thanks

    Thanks to everyone who contributed and made this release possible! Full list of
    people who contributed to this release can be found in the CHANGES file
    <https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=ca90c84e296ca82e2206eb86ed7364c588aad503;hb=602b6a7a27dca6990a38eb887e1d6615826387d5>.

.. _`PyPi release management page`: https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=apache-libcloud
