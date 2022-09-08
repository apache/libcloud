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

"""
Pylint plugin which tells Pylint how to work with driver classes.

At the moment, it supports the following scenarios:

1. It dynamically assigns "connection" class attribute on the NodeDriver
   class instance based on the value of "connectionCls" NodeDriver class
   attribute.
"""

from astroid import MANAGER, node_classes, scoped_nodes


def register(linter):
    pass


def transform(cls):
    if "NodeDriver" in cls.basenames:
        fqdn = cls.qname()
        module_name, _ = fqdn.rsplit(".", 1)

        # Assign connection class variable on it which is otherwise assigned
        # dynamically at the run time
        if "connectionCls" not in cls.locals:
            # connectionCls not explicitly defined on the driver class
            return

        connection_cls_name = cls.locals["connectionCls"][0].parent.value.name
        connection_cls_node = MANAGER.ast_from_module_name(module_name).lookup(connection_cls_name)[
            1
        ]

        if len(connection_cls_node) >= 1:
            if isinstance(connection_cls_node[0], node_classes.ImportFrom):
                # Connection class is imported and not directly defined in the driver class module
                connection_cls_module_name = connection_cls_node[0].modname
                connection_cls_node = MANAGER.ast_from_module_name(
                    connection_cls_module_name
                ).lookup(connection_cls_name)[1][0]

                cls.instance_attrs["connection"] = [connection_cls_node.instantiate_class()]
            else:
                # Connection class is defined directly in the driver module
                cls.instance_attrs["connection"] = [connection_cls_node[0].instantiate_class()]
            return


MANAGER.register_transform(scoped_nodes.ClassDef, transform)
