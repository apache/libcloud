# This example adds monitoring to a pool

import libcloud


def update_health_monitors(driver, network_domain, monitor_id):
    pool_name = "sdk_test_balancer"
    pools = driver.ex_get_pools(ex_network_domain_id=network_domain.id)
    pool = [p for p in pools if p.name == pool_name][0]
    pool.health_monitor_id = monitor_id
    result = lbdriver.ex_update_pool(pool)
    return result


def health_monitors(driver, network_domain):
    monitors = driver.ex_get_default_health_monitors(network_domain)
    return monitors


# Compute driver to create/edit virtual servers
cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
compute_driver = cls("my_username", "my_pass", region="eu")

# Load balancer driver to create and/or edit load balanceers
cls = libcloud.get_driver(libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS)

net_domain_name = "sdk_test_1"
net_domains = compute_driver.ex_list_network_domains(location="EU6")
net_domain_id = [d for d in net_domains if d.name == net_domain_name][0].id
lbdriver = cls("my_username", net_domain_id, "my_pass", region="eu")

# Get available health monitors
results = health_monitors(lbdriver, net_domains[0])
for result in results:
    print(result)

# Add desired health monitor
result = update_health_monitors(lbdriver, net_domains[0], "9f79487a-1b6d-11e5-8d4f-180373fb68df")
assert result is True
