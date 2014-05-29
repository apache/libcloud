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
from libcloud.compute.base import NodeAuthPassword

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
kwargs["ex_storage_service_name"]="mtlytics"
kwargs["ex_deployment_name"]="dcoddkinztest02"
kwargs["ex_deployment_slot"]="Production"
kwargs["ex_admin_user_id"]="azurecoder"
auth = NodeAuthPassword("Pa55w0rd", False)

kwargs["auth"]= auth

kwargs["size"]= "ExtraSmall"
kwargs["image"] = "5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415"
kwargs["name"] = "dc15"

node = type('Node', (object,), dict(id="dc14"))
#result = driver.create_node(ex_cloud_service_name="dcoddkinztest02", **kwargs)
result = driver.create_node(ex_cloud_service_name="testdc123", **kwargs)
#result = driver.create_cloud_service("testdc123", "North Europe")
#print(result.__repr__())
# reboot "test"
