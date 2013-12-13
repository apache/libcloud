host = 'example.com'
path = '/path/to/api'
Driver = get_driver(Provider.CLOUDSTACK)
conn = Driver(key=apikey, secret=secretkey, host=host, path=path)
