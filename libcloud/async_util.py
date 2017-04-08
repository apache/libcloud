# -*- coding: utf-8 -*-
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

import asyncio
import types

class AsyncSession(object):
    def __init__(self, cls):
        if isinstance(cls, tuple):
            self.classes = cls
        else:
            self.classes = [cls]

        # Replace the list_node methods with an awaitable
        for c in self.classes:
            async def async_list_nodes(self):
                return self._list_nodes()
            c._list_nodes = c.list_nodes
            c.list_nodes = types.MethodType(async_list_nodes, c)

    async def __aenter__(self):
        print('entering context')
        if len(self.classes) == 1:
            return self.classes[0]
        else:
            return self.classes

    async def __aexit__(self, exc_type, exc, tb):
        print('exiting context')
