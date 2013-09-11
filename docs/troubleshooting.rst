Troubleshooting
===============

.. _troubleshooting:

This page contains various tips which can help you troubleshoot and debug
code with interfaces with libcloud.

Debugging
---------

.. _debugging:

.. note::

    If you are sharing debug output on our IRC channel or issue tracker using
    Pastebin, Github Gists or a similar service, make sure to remove your
    credentials and any other data you consider private from the output.

Libcloud has a special debug mode which when enabled outputs all the outgoing
HTTP requests and all the incoming HTTP responses. Output also includes cURL
commands which can be used to re-produce the requests.

When this mode is enabled and if ``paramiko`` library is installed (used for
deployment), paramiko library log level is also set to ``DEBUG`` which helps
with debugging the deployment issues.

To enable it, set ``LIBCLOUD_DEBUG`` environment variable and make it point
to a file where the output should be saved.

For example if you want the output to be logged to the standard error (on
Unix) you can set it to ``/dev/stderr``:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr python my_script.py.

Example output:

.. sourcecode:: bash

    # -------- begin 4431824872 request ----------
    curl -i -X GET -H 'Host: s3.amazonaws.com' -H 'X-LC-Request-ID: 4431824872' -H 'Content-Length: 0' -H 'User-Agent: libcloud/0.6.0-beta1 (Amazon S3 (standard))' 'https://s3.amazonaws.com:443/?AWSAccessKeyId=foo&Signature=bar'
    # -------- begin 4431824872:4431825232 response ----------
    HTTP/1.1 200 OK
    X-Amz-Id-2: 1234
    Server: AmazonS3
    Transfer-Encoding: chunked
    X-Amz-Request-Id: FFFFFFFFFF
    Date: Tue, 01 Nov 2011 22:29:11 GMT
    Content-Type: application/xml

    171
    <?xml version="1.0" encoding="UTF-8"?>
    <ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Owner><ID>sada8932dsa8d30i</ID><DisplayName>kami</DisplayName></Owner><Buckets><Bucket><Name>test34324323</Name><CreationDate>2011-11-01T22:17:23.000Z</CreationDate></Bucket></Buckets></ListAllMyBucketsResult>
    0

    # -------- end 4431824872:4431825232 response ----------
