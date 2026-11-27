# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import TestCase
from urllib.parse import parse_qs, urlsplit

import requests_mock

from libcloud.backup.drivers.ebs import EBSBackupDriver


class EBSBackupDriverTests(TestCase):
    def test_regional_endpoint(self):
        for region, host in [
            ("ap-south-1", "ec2.ap-south-1.amazonaws.com"),
            ("cn-north-1", "ec2.cn-north-1.amazonaws.com.cn"),
        ]:
            with self.subTest(region=region):
                driver = EBSBackupDriver("access-key", "secret-key", region)
                self.assertEqual(driver.connection.host, host)
                self.assertEqual(driver.connection.service_name, "ec2")

    def test_list_recovery_points_uses_ec2_query_api(self):
        driver = EBSBackupDriver("access-key", "secret-key", "ap-south-1")
        target = driver.ex_get_target_by_volume_id("vol-123")
        xml = """<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <snapshotSet><item><snapshotId>snap-123</snapshotId><volumeId>vol-123</volumeId>
        <startTime>2026-11-01T12:00:00.000Z</startTime><progress>100%</progress>
        <tagSet><item><key>Name</key><value>backup</value></item></tagSet>
        </item></snapshotSet></DescribeSnapshotsResponse>"""
        with requests_mock.Mocker() as transport:
            transport.get("https://ec2.ap-south-1.amazonaws.com/", text=xml)
            points = driver.list_recovery_points(target)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].id, "snap-123")
        self.assertEqual(points[0].extra["tags"], {"Name": "backup"})
        query = parse_qs(urlsplit(transport.last_request.url).query)
        self.assertEqual(query["Action"], ["DescribeSnapshots"])
        self.assertEqual(query["Version"], ["2016-11-15"])
        self.assertEqual(query["Filter.1.Value.1"], ["vol-123"])
        self.assertIn(
            "/ap-south-1/ec2/aws4_request", transport.last_request.headers["Authorization"]
        )

    def test_list_recovery_points_empty(self):
        driver = EBSBackupDriver("access-key", "secret-key", "ap-south-1")
        target = driver.ex_get_target_by_volume_id("vol-123")
        xml = '<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/"><snapshotSet/></DescribeSnapshotsResponse>'
        with requests_mock.Mocker() as transport:
            transport.get("https://ec2.ap-south-1.amazonaws.com/", text=xml)
            self.assertEqual(driver.list_recovery_points(target), [])

    def test_list_target_jobs_filters_pending_snapshots(self):
        driver = EBSBackupDriver("access-key", "secret-key", "ap-south-1")
        target = driver.ex_get_target_by_volume_id("vol-123")
        xml = """<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <snapshotSet><item><snapshotId>snap-123</snapshotId><volumeId>vol-123</volumeId>
        <progress>25%</progress></item></snapshotSet></DescribeSnapshotsResponse>"""
        with requests_mock.Mocker() as transport:
            transport.get("https://ec2.ap-south-1.amazonaws.com/", text=xml)
            jobs = driver.list_target_jobs(target)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, "snap-123")
        self.assertEqual(jobs[0].progress, 25)
        query = parse_qs(urlsplit(transport.last_request.url).query)
        self.assertEqual(query["Filter.1.Value.1"], ["vol-123"])
        self.assertEqual(query["Filter.2.Name"], ["status"])
        self.assertEqual(query["Filter.2.Value.1"], ["pending"])
