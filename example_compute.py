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

import libcloud.security

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


libcloud.security.VERIFY_SSL_CERT = False

SUBSCRIPTION_ID = '5191b16a-673d-426c-8c55-fdd912858e4e'
KEY_FILE = 'C:\\Users\\david\\Desktop\\libcloud.pem'

Azure = get_driver(Provider.AZURE)
driver = Azure(SUBSCRIPTION_ID, KEY_FILE )

kwargs = dict()
kwargs["name"] = "oddkinztest2"
kwargs["size"] = "A0"
kwargs["image"] = ""

kwargs
#node["cloud_service_name"]="dcoddkinztest01"
#node["deployment_name"]="dcoddkinztest01"
kwargs = {}
#kwargs["ex_cloud_service_name"]="dcoddkinztest02"
kwargs["ex_storage_service_name"]="mlytics"
kwargs["ex_deployment_name"]="dcoddkinztest02"
kwargs["ex_deployment_slot"]="dcoddkinztest02"
kwargs["ex_admin_user_id"]="azurecoder"
kwargs["auth"]= type('Auth', (object,), dict(password="Pa55w0rd"))
kwargs["size"]= "A1"
kwargs["image"] = u"RightImage CentOS 6.5 x64 v13.5.3"
kwargs["name"] = "dcoddkinztest02"

result = driver.create_node(ex_cloud_service_name="dcoddkinztest02", **kwargs)
#result=driver.list_images()
print(result.__repr__())
# reboot "test"
