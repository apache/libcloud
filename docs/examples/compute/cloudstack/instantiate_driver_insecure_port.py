host = 'localhost'
path = '/path/to/api'
port = 8080
Driver = get_driver(Provider.CLOUDSTACK)
conn = Driver(key=apikey, secret=secretkey, host=host,
              path=path, port=port, secure=False)
