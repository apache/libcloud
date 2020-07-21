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

import unittest
from libcloud.compute.providers import Provider
from libcloud.compute.providers import get_driver


class TestApiOutscale(unittest.TestCase):
    cls = get_driver(Provider.OUTSCALE)
    driver = cls(key='my_key', secret='my_secret', region="my_region")

    def test_locations(self):
        response = self.driver.list_locations()
        self.assertEqual(response.status_code, 200)

    def test_public_ips(self):
        response = self.driver.list_public_ips()
        self.assertEqual(response.status_code, 200)

        response = self.driver.create_public_ip()
        self.assertEqual(response.status_code, 200)

        response = self.driver.delete_public_ip(public_ip=response.json()["PublicIp"]["PublicIp"])
        self.assertEqual(response.status_code, 200)

    def test_images(self):
        response = self.driver.create_image(image_name="image_name", vm_id="vm_id")
        self.assertEqual(response.status_code, 200)
        image_id = response.json()["Image"]["ImageId"]

        response = self.driver.get_image(image_id)
        self.assertEqual(response.status_code, 200)

        response = self.driver.delete_image(image_id)
        self.assertEqual(response.status_code, 200)

        response = self.driver.list_images()
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
