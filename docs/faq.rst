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

I want do add a new provider driver what should I do?
-----------------------------------------------------

For now the best thing to do is to look at an existing driver and test cases
for examples.

Libcloud currently supports more than 25 different providers. This means we
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

Last point is the most important one, because Libcloud acts as a lowest common
denominator and can be used with many different providers.
Sometimes it doesn't make sense to build a common Libcloud API even if multiple
providers offer a similar service. Usually the case is that the APIs are vastly
different and there aren't enough common points which would allow us to build a
cross-provider API which would still provide enough benefit to the end user.

If the API matches the criteria mentioned above you should send a proposal to
our :ref:`mailing list <mailing-list>` where we can discuss it further. Ideally proposal should also
contain a prototype of a driver for at least two different providers. This
help with making sure that API you designed is not biased against a single
provider.
