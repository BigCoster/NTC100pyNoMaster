import time
# import io
from serial import rs485
from os import path
import logging.handlers
from influxdb import InfluxDBClient
from influxdb import SeriesHelper
from serial.serialutil import CR
from configparser import ConfigParser
import sys
from list_serial_ports import serial_ports

# conf logging
levels = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR}
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
console = logging.StreamHandler()
console.setFormatter(formatter)
filehandler = logging.handlers.RotatingFileHandler('NTC100.log', maxBytes=1048576, backupCount=5)
# filehandler = logging.handlers.TimedRotatingFileHandler('NTC1001.log', when='M', backupCount=7)

filehandler.setFormatter(formatter)
log.addHandler(console)
log.addHandler(filehandler)

log.info('Start application')

config = ConfigParser()
# def values:
config['influxdb'] = {'host': 'localhost', 'port': '8086', 'user': 'root',
                      'pass': 'root', 'db': 'mydb', 'retention_days': '30'}
config['comport'] = {'name': 'COM1', 'boudrate': '57600'}
config['logging'] = {'level': 'INFO', '; available levels': ', '.join(levels.keys())}
config['rs485'] = {'number_devices': '5', 'polling_interval': '5', '; polling intrval in seconds, def value': '1',
                   'first_device': '1', '; first device it`s start address, def value': '1'}

if not path.exists('config.ini'):
    log.warning('No config! It will be created with def values...')
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
else:
    config.read('config.ini')
log.info('Logging level: ' + config['logging']['level'])
log.setLevel(config['logging']['level'])

myclient = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'],
                          config['influxdb']['user'], config['influxdb']['pass'],
                          config['influxdb']['db'])

tmp_data = {}
msges = ['Start', 'Reset', 'Onboa']
first_dev = int(config['rs485']['first_device'])
num_dev = int(config['rs485']['number_devices'])
poll_interval = int(config['rs485']['polling_interval'])


class MySeriesHelper(SeriesHelper):
    # Meta class stores time series helper configuration.
    class Meta:
        # The client should be an instance of InfluxDBClient.
        client = myclient
        # The series name must be a string. Add dependent fields/tags in curly brackets.
        # series_name = 'events.stats.{server_name}'
        series_name = 'NTC100'
        # Defines all the fields in this time series.
        fields = ['curr_temp', 'time_resp']
        # Defines all the tags for the series.
        tags = ['dev_addr']
        # Defines the number of data points to store prior to writing on the wire.
        bulk_size = 16
        # autocommit must be set to True when using bulk_size
        autocommit = True


try:
    ser = rs485.RS485(config['comport']['name'], config['comport']['boudrate'], timeout=0.5)
    ser.rs485_mode = rs485.RS485Settings()
    # sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1),newline='\r')

    while True:
        i = first_dev
        while i < (first_dev + num_dev):
            toport = '>%dG\r' % (i,)
            send_t = time.time()
            ser.write(toport.encode('ascii'))
            log.debug(toport)
            comm_data = inbytes = ser.read_until(terminator=CR, size=6)
            get_t = time.time() - send_t
            if inbytes:
                try:
                    inbytes = inbytes.decode("ascii")
                    if not (inbytes[:5] in msges):
                        log.debug(inbytes.strip() + ' ' + str(int(get_t * 1000)) + 'ms')
                        inbytes = inbytes.strip()
                        inbytes = inbytes.strip('<')
                        inbytes = inbytes.split(':')
                        MySeriesHelper(dev_addr=inbytes[0], curr_temp=int(inbytes[1]), time_resp=int(get_t * 1000 / 5))
                    else:
                        log.info(inbytes.strip())
                except Exception as msg:
                    log.warning('Corrupted ascii -> ' + repr(comm_data))
                    log.warning(msg)
            else:
                log.debug('TIMEOUT ' + str(int(get_t * 1000)) + 'ms')
            i += i
        try:
            MySeriesHelper.commit()
        except Exception as msg:
            log.error('Coul`d not connect to influxdb')
            log.error(msg)
        ser.flushInput()
        time.sleep(poll_interval)

except Exception as msg:
    log.error('Can`t open ' + config['comport']['name'])
    log.error(msg)
    log.error('Available ports: %s.', ', '.join(serial_ports()))

sys.exit()
