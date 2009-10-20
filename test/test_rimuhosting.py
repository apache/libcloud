# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
# Copyright 2009 RedRata Ltd

from libcloud.drivers.rimuhosting import RimuHostingNodeDriver
from test import MockHttp

import unittest
import httplib

class RimuHostingTest(unittest.TestCase):
    def setUp(self):
        RimuHostingNodeDriver.connectionCls.conn_classes = (None,
                                                            RimuHostingMockHttp)
        self.driver = RimuHostingNodeDriver('foo')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes),1)
        node = nodes[0]
        self.assertEqual(node.public_ip[0], "1.2.3.4")
        self.assertEqual(node.public_ip[1], "1.2.3.5")
        self.assertEqual(node.id, 88833465)
    
    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes),1)
        size = sizes[0]
        self.assertEqual(size.ram,950)
        self.assertEqual(size.disk,20)
        self.assertEqual(size.bandwidth,75)
        self.assertEqual(size.price,89.95)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images),6)
        image = images[0]
        self.assertEqual(image.name,"Debian 5.0 (aka Lenny, RimuHosting"\
                         " recommended distro)")
        self.assertEqual(image.id, "lenny")

    def test_reboot_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # Raises exception on failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)
    
    def test_create_node(self):
        # Raises exception on failure
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        self.driver.create_node("api.ivan.net.nz",image, size)

class RimuHostingMockHttp(MockHttp):
    def _r_orders(self,method,url,body,headers):
        body = """
        { "get_orders_response" : 
            { "status_message" : null
            , "status_code" : 200 
            , "error_info" : null 
            , "response_type" : "OK" 
            , "human_readable_message" : "Found 15 orders"
            , "response_display_duration_type" : "REGULAR",
            "about_orders" :
                [{ "order_oid" : 88833465
                , "domain_name" : "api.ivan.net.nz"
                , "slug" : "order-88833465-api-ivan-net-nz"
                , "billing_oid" : 96122465
                , "is_on_customers_own_physical_server" : false
                , "vps_parameters" : { "memory_mb" : 160
                    , "disk_space_mb" : 4096
                    , "disk_space_2_mb" : 0}
                , "host_server_oid" : "764"
                , "server_type" : "VPS"
                , "data_transfer_allowance" : { "data_transfer_gb" : 30
                    , "data_transfer" : "30"}
                , "billing_info" : { }
                , "allocated_ips" : { "primary_ip" : "1.2.3.4"
                    , "secondary_ips" : ["1.2.3.5","1.2.3.6"]}
                , "running_state" : "RUNNING"}]}}"""
    
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    def _r_pricing_plans(self,method,url,body,headers):
        body = """
         {"get_pricing_plans_response" : 
             { "status_message" : null
              , "status_code" : 200
              , "error_info" : null
              , "response_type" : "OK"
              , "human_readable_message" : "Here some pricing plans we are offering on new orders.&nbsp; Note we offer most disk and memory sizes.&nbsp; So if you setup a new server feel free to vary these (e.g. different memory, disk, etc) and we will just adjust the pricing to suit.&nbsp; Pricing is in USD.&nbsp; If you are an NZ-based customer then we would need to add GST."
              , "response_display_duration_type" : "REGULAR"
              , "pricing_plan_infos" : 
                  [{ "pricing_plan_code" : "MiroVPSLowContention"
                    , "pricing_plan_description" : "MiroVPS Semi-Dedicated Server (Dallas)"
                    , "monthly_recurring_fee_usd" : 89.95
                    , "minimum_memory_mb" : 950
                    , "minimum_disk_gb" : 20
                    , "minimum_data_transfer_allowance_gb" : 75
                    , "see_also_url" : "http://rimuhosting.com/order/serverdetails.jsp?plan=MiroVPSLowContention"
                    , "server_type" : "VPS"
                    , "offered_at_data_center" : 
                        { "data_center_location_code" : "DCDALLAS"
                        , "data_center_location_name" : "Dallas"}}
                ]}}

        """

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_distributions(self, method, url, body, headers):
        body = """
        { "get_distros_response" : { "status_message" : null
  , "status_code" : 200
  , "error_info" : null
  , "response_type" : "OK"
  , "human_readable_message" : "Here are the distros we are offering on new orders."
  , "response_display_duration_type" : "REGULAR"
  , "distro_infos" : [{ "distro_code" : "lenny"
        , "distro_description" : "Debian 5.0 (aka Lenny, RimuHosting recommended distro)"}
    , { "distro_code" : "centos5"
        , "distro_description" : "Centos5"}
    , { "distro_code" : "ubuntu904"
        , "distro_description" : "Ubuntu 9.04 (Jaunty Jackalope, from 2009-04)"}
    , { "distro_code" : "ubuntu804"
        , "distro_description" : "Ubuntu 8.04 (Hardy Heron, 5 yr long term support (LTS))"}
    , { "distro_code" : "ubuntu810"
        , "distro_description" : "Ubuntu 8.10 (Intrepid Ibex, from 2008-10)"}
    , { "distro_code" : "fedora10"
        , "distro_description" : "Fedora 10"}]}}
        """
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_new_vps(self, method, url, body, headers):
        body = """
    { "post_new_vps_response" : 
        { "status_message" : null
          , "status_code" : 200
          , "error_info" : null
          , "response_type" : "OK"
          , "human_readable_message" : null
          , "response_display_duration_type" : "REGULAR"
          , "setup_messages" : 
              ["Using user-specified billing data: Wire Transfer" , "Selected user as the owner of the billing details: Ivan Meredith"
            , "No VPS paramters provided, using default values."]
          , "about_order" : 
              { "order_oid" : 52255865
              , "domain_name" : "api.ivan.net.nz"
              , "slug" : "order-52255865-api-ivan-net-nz"
              , "billing_oid" : 96122465
              , "is_on_customers_own_physical_server" : false
              , "vps_parameters" : 
                  { "memory_mb" : 160
                  , "disk_space_mb" : 4096
                  , "disk_space_2_mb" : 0}
              , "host_server_oid" : "764"
              , "server_type" : "VPS"
              , "data_transfer_allowance" :
                  { "data_transfer_gb" : 30 , "data_transfer" : "30"}
              , "billing_info" : { }
              , "allocated_ips" : 
                  { "primary_ip" : "74.50.57.80", "secondary_ips" : []}
              , "running_state" : "RUNNING"}
          , "new_order_request" : 
              { "billing_oid" : 96122465
              , "user_oid" : 0
              , "host_server_oid" : null
              , "vps_order_oid_to_clone" : 0
              , "ip_request" : 
                  { "num_ips" : 1, "extra_ip_reason" : ""}
              , "vps_parameters" : 
                  { "memory_mb" : 160
                  , "disk_space_mb" : 4096
                  , "disk_space_2_mb" : 0}
              , "pricing_plan_code" : "MIRO1B"
              , "instantiation_options" : 
                  { "control_panel" : "webmin"
                  , "domain_name" : "api.ivan.net.nz"
                  , "password" : "aruxauce27"
                  , "distro" : "lenny"}}
          , "running_vps_info" : 
              { "pings_ok" : true
              , "current_kernel" : "default"
              , "current_kernel_canonical" : "2.6.30.5-xenU.i386"
              , "last_backup_message" : ""
              , "is_console_login_enabled" : false
              , "console_public_authorized_keys" : null
              , "is_backup_running" : false
              , "is_backups_enabled" : true
              , "next_backup_time" : 
                  { "ms_since_epoch": 1256446800000, "iso_format" : "2009-10-25T05:00:00Z", "users_tz_offset_ms" : 46800000}
              , "vps_uptime_s" : 31
              , "vps_cpu_time_s" : 6
              , "running_state" : "RUNNING"
              , "is_suspended" : false}}}

        """
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_order_88833465_api_ivan_net_nz_vps(self, method, url, body, headers):
        body = """
        { "delete_server_response" : 
            { "status_message" : null
            , "status_code" : 200
            , "error_info" : null
            , "response_type" : "OK"
            , "human_readable_message" : "Server removed"
            , "response_display_duration_type" : "REGULAR"
            , "cancel_messages" : 
                ["api.ivan.net.nz is being shut down."
                , "A $7.98 credit has been added to your account."
                , "If you need to un-cancel the server please contact our support team."]
            }
        }

        """
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _r_orders_order_88833465_api_ivan_net_nz_vps_running_state(self, method,
                                                                   url, body,
                                                                   headers):
        
        body = """
        { "put_running_state_response" : 
            { "status_message" : null
              , "status_code" : 200
              , "error_info" : null
              , "response_type" : "OK"
              , "human_readable_message" : "api.ivan.net.nz restarted.  After the reboot api.ivan.net.nz is pinging OK."
              , "response_display_duration_type" : "REGULAR"
              , "is_restarted" : true
              , "is_pinging" : true
              , "running_vps_info" : 
                  { "pings_ok" : true
                  , "current_kernel" : "default"
                  , "current_kernel_canonical" : "2.6.30.5-xenU.i386"
                  , "last_backup_message" : ""
                  , "is_console_login_enabled" : false
                  , "console_public_authorized_keys" : null
                  , "is_backup_running" : false
                  , "is_backups_enabled" : true
                  , "next_backup_time" : 
                      { "ms_since_epoch": 1256446800000, "iso_format" : "2009-10-25T05:00:00Z", "users_tz_offset_ms" : 46800000}
                  , "vps_uptime_s" : 19
                  , "vps_cpu_time_s" : 5
                  , "running_state" : "RUNNING"
                  , "is_suspended" : false}
              , "host_server_info" : { "is_host64_bit_capable" : true
                  , "default_kernel_i386" : "2.6.30.5-xenU.i386"
                  , "default_kernel_x86_64" : "2.6.30.5-xenU.x86_64"
                  , "cpu_model_name" : "Intel(R) Xeon(R) CPU           E5506  @ 2.13GHz"
                  , "host_num_cores" : 1
                  , "host_xen_version" : "3.4.1"
                  , "hostload" : [1.45
                    , 0.56
                    , 0.28]
                  , "host_uptime_s" : 3378276
                  , "host_mem_mb_free" : 51825
                  , "host_mem_mb_total" : 73719
                  , "running_vpss" : 34}
              , "running_state_messages" : null}}

        """
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

