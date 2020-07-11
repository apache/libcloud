:orphan:

Pricing
=======

For majority of the compute providers Libcloud provides estimated pricing
information. Pricing information is available via the :attr:`price` attribute
on the :class:`NodeSize` object. :attr:`price` attribute is a :func:`float`
type and tells user how much it costs (in US dollars) to run a ``Node`` with a
specified :class:`NodeSize` for an hour.

Example below shows how to retrieve pricing for ``NodeSize`` objects using
:func:`list_sizes` method.

.. literalinclude:: /examples/compute/pricing.py
   :language: python
   :emphasize-lines: 11-18

As noted above this pricing information is an estimate and should only
be used as such. You should always check your provider website / control panel
for accurate pricing information and never rely solely on Libcloud pricing data.

Besides that, many cloud providers also offer different pricing scheme based
on the volume, term commitment and discounts for reserved instances. All of
this information is not taken into account in the simplistic "price per hour"
pricing scheme available in Libcloud.

Where does the Libcloud pricing data come from?
-----------------------------------------------

Most of the providers don't provide pricing information via the API which means
most of the pricing information is scraped directly from the provider
websites.

Pricing data which is scraped from the provider websites is located in a
JSON file (``data/pricing.json``) which is bundled with each release. This
pricing data is only updated once you install a new release which means it
could be out of date.

Downloading latest pricing data from an S3 Bucket
-------------------------------------------------

Since July 2020, we now run a daily job as part of our CI/CD system which
scrapes pricing data for various providers and publishes pricing data to a
public read-only S3 bucket.

Pricing file data is available at the following locations:

* https://libcloud-pricing-data.s3.amazonaws.com/pricing.json
* https://libcloud-pricing-data.s3.amazonaws.com/pricing.json.sha256
* https://libcloud-pricing-data.s3.amazonaws.com/pricing.json.sha512

First file contains the actual pricing JSON file and the second and third
contain SHA 256 and SHA 512 sum of that file content.

We are providing this service free of charge so it's important that you don't
abuse it. This means you should not download this file more than once per day
(it makes no sense to do it more often, since it only gets updated once per
day if there are any changes) and you should utilize one of the caching
approaches described below and only download ``pricing.json`` file when there
are any changes / updates.

You can use the content of the sha sum files to implement efficient file
downloads and only download pricing.json file if the content has changed.

You can do that by fetching the sha sum file, caching the sha sum and only
downloading ``pricing.json`` file is the sha sum value has changed.

An alternative to using the content of the sha sum file is caching the value
of the ``ETag`` HTTP response header which you can retrieve by issuing HTTP
``HEAD`` request against the ``pricing.json`` URL. HEAD request will only
return the object metadata without the actual content.

For example:

.. sourcecode:: bash

    curl --head https://libcloud-pricing-data.s3.amazonaws.com/pricing.json

    HTTP/1.1 200 OK
    x-amz-id-2: c8Mer3VtRYWGeKtKlbgwebn3BsVQt+Z/WKKPjk3NcsRSK23BzE6OQDIogzIR2oJGJRmOtS4ydjA=
    x-amz-request-id: 9A790A3B3587478D
    Date: Sat, 11 Jul 2020 16:01:39 GMT
    Last-Modified: Sat, 11 Jul 2020 15:55:50 GMT
    ETag: "e46324663d76dedafc7d9b09537b18a7"
    Accept-Ranges: bytes
    Content-Type: application/json
    Content-Length: 549390
    Server: AmazonS3

.. _using-custom-pricing-file:

Using a custom pricing file
---------------------------

.. note::

    This functionality is only available in Libcloud 0.14.0 and above.

By default Libcloud reads pricing data from ``data/pricing.json`` file which
is included in the release package. If you want to use a custom pricing file,
simply move your custom pricing file to ``~/.libcloud.pricing.json``.

If ``~/.libcloud.pricing.json`` file is available, Libcloud will use it instead
of the default pricing file which comes bundled with the release.

Updating pricing
----------------

.. note::

    This functionality is only available in Libcloud 0.14.0 and above.

Currently only way to update pricing is programmatically using
:func:`libcloud.pricing.download_pricing_file` function. By default this
function retrieves the latest pricing file from our git repository and saves it
to ``~/.libcloud.pricing.json``.

.. autofunction:: libcloud.pricing.download_pricing_file
