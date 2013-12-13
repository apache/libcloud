url = 'http://example.com/path/to/api'
Driver = get_driver(Provider.CLOUDSTACK)
conn = Driver(key=apikey, secret=secretkey, url=url)
