Troubleshooting
===============

.. _troubleshooting:

This page contains various tips which can help you troubleshoot and debug
code with interfaces with libcloud.

Debugging
---------

.. _debugging:

.. note::

    If you are sharing debug output on any public medium such as our IRC
    channel or an issue tracker using Pastebin, Github Gists or a similar
    service, make sure to remove your credentials and any other data you
    consider private from the output.

Libcloud has a special debug mode which when enabled, logs all the outgoing
HTTP requests and all the incoming HTTP responses. Output also includes cURL
commands which can be used to re-produce the requests.

When this mode is enabled and ``paramiko`` library is installed (used for
deployment), paramiko library log level is set to ``DEBUG`` which helps with
debugging the deployment related issues.

To make the debugging easier, Libcloud will also automatically decompress the
response body (if compressed) before logging it.

To enable it, set ``LIBCLOUD_DEBUG`` environment variable and make it point
to a file where the debug output should be saved.

If the API returns JSON or XML in the response body which is not human
friendly, you can also set ``LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE``
environment variable which will cause the JSON or XML to be beautified
/ formated so it's easier for humans to read it. Keep in mind that this
only works for non-chunked responses.

Example 1 - Logging output to standard error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want the output to be logged to the standard error (on
Linux) you can set it to ``/dev/stderr``:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr python my_script.py

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

Example 2 - Making JSON / XML response human friendly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Non-formatted JSON response:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr python my_script.py

.. sourcecode:: bash

    # -------- begin 23125648:23160304 response ----------
    HTTP/1.1 200 OK
    Content-Length: 1572
    X-Compute-Request-Id: req-79ab42d8-a959-44eb-8dec-bc9458b2f4b3
    Server: nginx/1.4.7
    Connection: keep-alive
    Date: Sat, 06 Sep 2014 14:13:37 GMT
    Content-Type: application/json

    {"servers": [{"status": "ACTIVE", "updated": "2014-09-06T14:13:32Z", "hostId": "561d56de25c177c422278d7ca5f8b210118348040b12afbad06f278a", "addresses": {"internet-routable": [{"OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:3f:c0:a1", "version": 4, "addr": "10.100.100.101", "OS-EXT-IPS:type": "fixed"}]}, "links": [{"href": "http://nova/v2/d3b31ebfd32744d19d848f3e9c351869/servers/deb35f96-be41-431e-b931-6e615ec720f4", "rel": "self"}, {"href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/servers/deb35f96-be41-431e-b931-6e615ec720f4", "rel": "bookmark"}], "key_name": null, "image": {"id": "e9537ddd-6579-4473-9898-d211ab90f6d3", "links": [{"href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/images/e9537ddd-6579-4473-9898-d211ab90f6d3", "rel": "bookmark"}]}, "OS-EXT-STS:task_state": null, "OS-EXT-STS:vm_state": "active", "OS-SRV-USG:launched_at": "2014-09-06T14:13:32.000000", "flavor": {"id": "90c2a137-611b-4dd2-9d65-d4a0b0858531", "links": [{"href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/flavors/90c2a137-611b-4dd2-9d65-d4a0b0858531", "rel": "bookmark"}]}, "id": "deb35f96-be41-431e-b931-6e615ec720f4", "security_groups": [{"name": "default"}], "OS-SRV-USG:terminated_at": null, "OS-EXT-AZ:availability_zone": "nova", "user_id": "06dda7c06aa246c88d7775d02bc119ac", "name": "test lc 2", "created": "2014-09-06T14:13:12Z", "tenant_id": "d3b31ebfd32744d19d848f3e9c351869", "OS-DCF:diskConfig": "MANUAL", "os-extended-volumes:volumes_attached": [], "accessIPv4": "", "accessIPv6": "", "progress": 0, "OS-EXT-STS:power_state": 1, "config_drive": "", "metadata": {}}]}
    # -------- end 23125648:23160304 response ----------

Human friendly formatted JSON response:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE=1 python my_script.py

.. sourcecode:: bash

    # -------- begin 41102928:41133624 response ----------
    HTTP/1.1 200 OK
    Content-Length: 1572
    X-Compute-Request-Id: req-3ce8b047-55cd-4e20-bfeb-b65619696aec
    Server: nginx/1.4.7
    Connection: keep-alive
    Date: Sat, 06 Sep 2014 14:14:38 GMT
    Content-Type: application/json

    {
        "servers": [
            {
                "OS-DCF:diskConfig": "MANUAL",
                "OS-EXT-AZ:availability_zone": "nova",
                "OS-EXT-STS:power_state": 1,
                "OS-EXT-STS:task_state": null,
                "OS-EXT-STS:vm_state": "active",
                "OS-SRV-USG:launched_at": "2014-09-06T14:13:32.000000",
                "OS-SRV-USG:terminated_at": null,
                "accessIPv4": "",
                "accessIPv6": "",
                "addresses": {
                    "internet-routable": [
                        {
                            "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:3f:c0:a1",
                            "OS-EXT-IPS:type": "fixed",
                            "addr": "10.100.100.101",
                            "version": 4
                        }
                    ]
                },
                "config_drive": "",
                "created": "2014-09-06T14:13:12Z",
                "flavor": {
                    "id": "90c2a137-611b-4dd2-9d65-d4a0b0858531",
                    "links": [
                        {
                            "href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/flavors/90c2a137-611b-4dd2-9d65-d4a0b0858531",
                            "rel": "bookmark"
                        }
                    ]
                },
                "hostId": "561d56de25c177c422278d7ca5f8b210118348040b12afbad06f278a",
                "id": "deb35f96-be41-431e-b931-6e615ec720f4",
                "image": {
                    "id": "e9537ddd-6579-4473-9898-d211ab90f6d3",
                    "links": [
                        {
                            "href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/images/e9537ddd-6579-4473-9898-d211ab90f6d3",
                            "rel": "bookmark"
                        }
                    ]
                },
                "key_name": null,
                "links": [
                    {
                        "href": "http://nova/v2/d3b31ebfd32744d19d848f3e9c351869/servers/deb35f96-be41-431e-b931-6e615ec720f4",
                        "rel": "self"
                    },
                    {
                        "href": "http://nova/d3b31ebfd32744d19d848f3e9c351869/servers/deb35f96-be41-431e-b931-6e615ec720f4",
                        "rel": "bookmark"
                    }
                ],
                "metadata": {},
                "name": "test lc 2",
                "os-extended-volumes:volumes_attached": [],
                "progress": 0,
                "security_groups": [
                    {
                        "name": "default"
                    }
                ],
                "status": "ACTIVE",
                "tenant_id": "d3b31ebfd32744d19d848f3e9c351869",
                "updated": "2014-09-06T14:13:32Z",
                "user_id": "06dda7c06aa246c88d7775d02bc119ac"
            }
        ]
    }
    # -------- end 41102928:41133624 response ----------

Non-formatted XML response:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr python my_script.py

.. sourcecode:: bash

    # -------- begin 33145616:33126160 response ----------
    HTTP/1.1 200 OK
    X-Amzn-Requestid: e84f62d0-368e-11e4-820b-8bf013dc269e
    Date: Sun, 07 Sep 2014 13:00:13 GMT
    Content-Length: 457
    Content-Type: text/xml

    <?xml version="1.0"?>
    <ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/"><HostedZones><HostedZone><Id>/hostedzone/Z14L0C73CHH1DN</Id><Name>example1.com.</Name><CallerReference>41747982-568E-0DFC-8C11-71C23757C740</CallerReference><Config><Comment>test</Comment></Config><ResourceRecordSetCount>9</ResourceRecordSetCount></HostedZone></HostedZones><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListHostedZonesResponse>
    # -------- end 33145616:33126160 response ----------

Human friendly formatted XML response:

.. sourcecode:: bash

    LIBCLOUD_DEBUG=/dev/stderr LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE=1 python my_script.py

.. sourcecode:: bash

    # -------- begin 19444496:19425040 response ----------
    HTTP/1.1 200 OK
    X-Amzn-Requestid: 01c02441-368f-11e4-b616-9b9bd7509a8f
    Date: Sun, 07 Sep 2014 13:00:56 GMT
    Content-Length: 457
    Content-Type: text/xml

    <?xml version="1.0" ?>
    <ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
        <HostedZones>
            <HostedZone>
                <Id>/hostedzone/Z14L0C73CHH1DN</Id>
                <Name>example1.com.</Name>
                <CallerReference>41747982-568E-0DFC-8C11-71C23757C740</CallerReference>
                <Config>
                    <Comment>test</Comment>
                </Config>
                <ResourceRecordSetCount>9</ResourceRecordSetCount>
            </HostedZone>
        </HostedZones>
        <IsTruncated>false</IsTruncated>
        <MaxItems>100</MaxItems>
    </ListHostedZonesResponse>

    # -------- end 19444496:19425040 response ----------
