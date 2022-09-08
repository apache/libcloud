from libcloud.compute.providers import get_driver, set_driver

set_driver("stratuslab", "stratuslab.libcloud.stratuslab_driver", "StratusLabNodeDriver")

# Your code which uses the driver.
# For example:
driver = get_driver("stratuslab")
