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

import json

from bottle import route

from integration.compute.api.data import NODES, REPORT_DATA
from integration.compute.api.util import secure


@route("/compute/nodes", method="GET")
@secure
def list_nodes():
    return json.dumps(NODES)


@route("/compute/report_data", method="GET")
@secure
def ex_report_data():
    return REPORT_DATA
