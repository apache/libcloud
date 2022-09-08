# This example assumes servers to load balance
# already exist and will be pool members
import libcloud
from libcloud.loadbalancer.base import Algorithm


def create_load_balancer():
    # Compute driver to retrieve servers to be pool members (the nodes)
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    compute_driver = cls("my_username", "my_pass", region="eu")
    net_domain_name = "sdk_test_1"
    net_domains = compute_driver.ex_list_network_domains(location="EU6")
    net_domain_id = [d for d in net_domains if d.name == net_domain_name][0].id
    # Load balancer driver to create and/or edit load balanceers
    cls = libcloud.get_driver(
        libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS
    )
    lbdriver = cls("my_username", net_domain_id, "my_pass", region="eu")

    member1 = compute_driver.list_nodes(ex_name="web1")[0]
    member2 = compute_driver.list_nodes(ex_name="web2")[0]
    members = [member1, member2]
    name = "sdk_test_balancer"
    port = "80"
    listener_port = "8000"
    protocol = "TCP"
    algorithm = Algorithm.LEAST_CONNECTIONS_MEMBER
    members = [m for m in members]
    ex_listener_ip_address = "168.128.13.127"
    lb = lbdriver.create_balancer(
        name,
        listener_port=listener_port,
        port=port,
        protocol=protocol,
        algorithm=algorithm,
        members=members,
        optimization_profile="TCP",
        ex_listener_ip_address=ex_listener_ip_address,
    )
    print(lb)
