from influxdb import InfluxDBClient
from configparser import ConfigParser
from os import path

config = ConfigParser()

config = ConfigParser()
# def values:
config['influxdb'] = {'host': 'localhost', 'port': '8086', 'user': 'root',
                      'pass': 'root', 'db': 'mydb','retention_days':'30'}
config['comport'] = {'name': 'COM1', 'boudrate': '57600'}
config['logging'] = {'enabled':'True'}

if not path.exists('config.ini'):
    print(timenow(), 'No config! It will be created with def values...')
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
else:
    config.read('config.ini')
    
myclient = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'],
                          config['influxdb']['user'], config['influxdb']['pass'],
                          config['influxdb']['db'])


# myclient.drop_database(config['influxdb']['db'])
myclient.create_database(config['influxdb']['db'])
myclient.create_retention_policy('awesome_policy', 
	config['influxdb']['retention_days'] + 'd', 3, default=True)