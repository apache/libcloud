Frequently Asked Questions (FAQ)
================================

Why are the block storage related management methods located in the compute API?
--------------------------------------------------------------------------------

Block storage related management methods are located in the compute API because
in most cases block storage API is tightly coupled with the compute API meaning
that you can't manage block storage independent of the compute API.

This also makes sense because in most cases you are only interested in attaching
or detaching volumes from and to the compute nodes.

What are the extension methods and arguments?
---------------------------------------------

Libcloud acts as a lowest common denominator and exposes a unified base API
which allows you to work with many different cloud providers through a single
code base.

Being a lowest common denominator by definition means that not all of the
functionality offered by different cloud service providers is available
through a base API.

Libcloud solves this problem and allows user to access provider specific
functionality through a so called extension methods and arguments. Extension
methods and arguments are all the methods and arguments which are prefixed
with ``ex_``.

Extension methods are there for your convenience, but you should be careful
when you use them because they make switching or working with multiple
providers harder.

How do I test if provider credentials are valid?
------------------------------------------------

Libcloud makes the whole authentication process transparent to the user. As
such, the easiest way to check if provider credentials are valid is by
instantiating a driver and calling a method which results in an HTTP call.

If the credentials are valid, method will return a result, otherwise
:class:`libcloud.common.types.InvalidCredsError` exception will be thrown.

An example of such method is
:func:`libcloud.compute.base.NodeDriver.list_nodes`. Keep in mind that depending
on the account state, list_nodes method might return a lot of data.

If you want to avoid unnecessarily fetching a lot of data, you should find a
method specific to your provider which issues a request which results in small
amount of data being retrieved.

I want do add a new provider driver what should I do?
-----------------------------------------------------

For now the best thing to do is to look at an existing driver and test cases
for examples.

Libcloud currently supports more than 60 different providers. This means we
have a broad range of examples of different APIs and authentication methods.
APIs range from simple JSON based REST APIs to SOAP APIs. Authentication
methods range from simple shared token and digest auth to HMAC signed requests.

I want to add / propose a new API, what should I do?
----------------------------------------------------

We are always open to accepting a now top level API as long as it matches the
following criteria:

1. API must be indented to manage an online infrastructure oriented Cloud
   service
2. Similar service is offered by multiple providers
3. It's possible to build a common API on top of services provided by different
   services

Libcloud can be used with many different providers and acts as a lowest common
denominator which makes the last point most important one. Sometimes it doesn't
make sense to build a common Libcloud API even if multiple providers offer a
similar service. Usually the case is that the APIs are vastly different and
there aren't enough common points which would allow us to build a
cross-provider API which would still provide enough value to the end user.

If the API matches the criteria defined above, you should send a proposal to
our :ref:`mailing list <mailing-lists>` where we can discuss it further.
Ideally, the proposal should also contain a prototype of a driver for at least
two different providers. This helps us make sure that the API you have designed
is not biased towards a single provider.

How do I obtain Libcloud version?
---------------------------------

You can obtain currently active Libcloud version by accessing the
``libcloud.__version__`` variable.

Example #1 (command line):

.. sourcecode:: bash

    python -c "import libcloud ; print libcloud.__version__"

Example #2 (code):

.. sourcecode:: python

    import libcloud
    libcloud.__version__

