#!/usr/bin/env python

from array import array
from collections import namedtuple
import json
import os
import sys
import time
import datetime
import yaml

import click
from halo import Halo

import utils
import paho.mqtt.client as mqtt

MQTT_BROKER_HOST = 'mqtt.eclipse.org'
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = 'bloc/demo'


sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
import SmartMeshSDK.ApiException
from SmartMeshSDK.IpMgrConnectorSerial import IpMgrConnectorSerial
from SmartMeshSDK.IpMgrConnectorMux.IpMgrSubscribe import IpMgrSubscribe
from SmartMeshSDK.protocols.Hr.HrParser import HrParser
from SmartMeshSDK.protocols.blink import blink

LOG_DIR_NAME = 'logs'
current_burst_id='abcdef'
new_burst = True
first_burst = True
burst_max_rssi=-200
burst_closest_neighbor ={}
position={"timestamp": "02/13/20 16:09:00", "tag": "00-17-0d-00-00-38-03-69", "type": "tag-position", "anchor": "00-17-0D-00-00-31-C3-71"}
position_set=False


tag = {'macAddress':'00-17-0d-00-00-38-03-69'}
# See "Factory Default Settings", Section 3.7 of SmartMesh IP User's Guide
DEFAULT_JOIN_KEY = (
    0x44, 0x55, 0x53, 0x54, 0x4E, 0x45, 0x54, 0x57,
    0x4F, 0x52, 0x4B, 0x53, 0x52, 0x4F, 0x43, 0x4B
)
# See libs/SmartMeshSDK/protocols/blink/blink.py
BLINK_PAYLOAD_COMMAND_ID = 0x94

class MqttManager:


    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
    def connect(self):
        self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    def _send_blink_update(self, message):
        print('publish message: {}'.format(message))
        self.client.publish(MQTT_TOPIC, json.dumps(message))

    def _on_connect(self, client, userdata, flags, rc):
        print('connected')
        client.subscribe(MQTT_TOPIC)
        print('subscribe to {}'.format(MQTT_TOPIC))

    def _on_message(self, client, userdata, message):

        msg = json.loads(message.payload)
        #if ('type' in msg) and (msg['type'] == 'req-config'):
        #    self.client.publish(MQTT_TOPIC, json.dumps({'type': 'res-config', 'config': self.config}))
        #else:
        #    pass
        #self._send_blink_update(position)

def convert_mac_addr_to_tuple(mac_addr):
    # input : (mac_addr) 'XX-XX-XX-XX-XX-XX-XX-XX'
    # output: (tuple)    (XX, XX, XX, XX, XX, XX, XX)
    return tuple(map(lambda s: int(s, 16), mac_addr.split('-')))

def connect_manager(serial_dev):
    # prepaer and return a ready-to-use IpMgrConnectorSerial object
    spinner = Halo(text='Connecting to Manager')
    spinner.start()

    manager = IpMgrConnectorSerial.IpMgrConnectorSerial()

    try:
        manager.connect({'port': serial_dev})
    except SmartMeshSDK.ApiException.ConnectionError:
        spinner.fail()
        msg = (
            'Cannot establish connection to {}.\n'.format(serial_dev) +
            'Is this the right port for "API" of the manager?\n' +
            'You may have specified the port for "CLI".\n'
        )
        sys.exit(msg)

    spinner.succeed('Manager is ready')
    return manager

def prepare_log_file():
    spinner = Halo(text='Preparing a log file')
    log_dir_path = os.path.join(utils.get_blink_base_path(), LOG_DIR_NAME)

    # make sure we have the log directory
    if os.path.isdir(log_dir_path):
        # log directory is ready :-)
        pass
    else:
        try:
            os.mkdir(log_dir_path)
        except OSError as err:
            spinner.fail()
            sys.exit('Failed to make the log directory: {}'.format(err))

    # decide a log file name and create it
    log_file_name = 'log-blink-manager-{}.jsonl'.format(
        time.strftime('%Y%m%d-%H%M%S')
    )
    log_file_path = os.path.join(log_dir_path, log_file_name)
    if os.path.exists(log_file_path):
        spinner.fail()
        msg = (
            'Failed to crate a log file.\n' +
            'Log file already exits: {}'.format(log_file_path)
        )
        sys.exit(msg)
    else:
        # create an empty file with the log file name
        try:
            open(log_file_path, 'w').close()
        except OSError as err:
            spinner.fail()
            sys.exit('Failed to create a log file: {}'.format(err))

    spinner.succeed(
        'Log file is ready: {}'.format(os.path.relpath(log_file_path))
    )
    return log_file_path

def setup_acl(manager, config):
    # - clear ACL (for a case when we change the list of anchors)
    # - add ACL entries for the anchors
    # - add an ACL entry for the tag
    spinner = Halo(text='Setting up ACK')
    spinner.start()

    spinner.text = 'Clearing ACL'
    ALL_MOTES = (0, 0, 0, 0, 0, 0, 0, 0)
    try:
        manager.dn_deleteACLEntry(ALL_MOTES)
    except SmartMeshSDK.ApiException.APIError as err:
        spinner.fail()
        sys.exit('Failed to clear ACL: {}'.format(err))

    spinner.text = 'Adding ACL entries'
    # anchor entry is two-element list: [0] is MAC address, [1] is location
    mote_list = [config.tag] + [anchor[0] for anchor in config.anchors]
    for mote in mote_list:
        try:
            manager.dn_setACLEntry(
                macAddress = convert_mac_addr_to_tuple(mote),
                joinKey    = DEFAULT_JOIN_KEY
            )
        except SmartMeshSDK.ApiException.APIError as err:
            spinner.fail()
            sys.exit('Failed to add an ACL entry for {}'.format(mote))

    spinner.succeed(
        '{0} ACL {1} installed'.format(
            len(mote_list),
            'entry is' if len(mote_list) == 0 else 'entries are'
        )
    )
    return

def convert_mote_id_to_mac_address(manager, mote_id):
    ret = manager.dn_getMoteConfigById(mote_id)
    return '-'.join(map(lambda x: '%02x' % x, ret.macAddress))

def it_is_blink_packet_log(log):
    return (
        log['type'] == IpMgrSubscribe.NOTIFDATA
        and
        'data' in log['params']
        and
        log['params']['data'][0] == blink.BLINK_PAYLOAD_COMMAND_ID
    )

def get_anchor_location(anchors, mac_addr):
    if mac_addr in anchors:
        ret_val = anchors[mac_addr]
    else:
        ret_val = "N/A"

    return ret_val

#parses the blink packet and returns the closest neighbor
def parse_blink_packet(manager, anchors, log):
    payload = ''.join([chr(b) for b in log['params']['data']])
    user_input, neighbors = blink.decode_blink(payload)
    new_neighbors = []
    closest_neighbor = 0
    max_rssi=-200
    
    for mote_id, rssi in neighbors:
        if (int(rssi)>int(max_rssi)):
            max_rssi=rssi
            print 'found better rssi in blink packet'
            print rssi
            mac_addr = convert_mote_id_to_mac_address(manager, mote_id)
            closest_neighbor = {
                'macAddress': mac_addr,
                'location': get_anchor_location(anchors, mac_addr),
                'rssi': rssi
            }
        new_neighbors.append({
            'macAddress': mac_addr,
            'location': get_anchor_location(anchors, mac_addr),
            'rssi': rssi
        })
    for neighbor in new_neighbors:
        print neighbor
    print '---'
    print 'closest neighbor'
    print str(closest_neighbor)

    return {
        'subtype': 'blink',
        'user_input': user_input,
        'neighbors': new_neighbors,
        'closest_neighbor':closest_neighbor
        },user_input

def parse_health_report_packet(manager, health_report_parser, log):
    payload = array('B', log['params']['payload'])
    ret = health_report_parser.parseHr(payload)
    for key in ret:
        if key in ['Neighbors', 'Discovered']:
            if key == 'Neighbors':
                subkey = 'neighbors'
            else:
                subkey = 'discoveredNeighbors'
            for neighbor in ret[key][subkey]:
                neighbor['macAddress'] = convert_mote_id_to_mac_address(
                    manager,
                    neighbor['neighborId']
                )
        else:
            # do nothing
            pass
    return ret

def subscribe_notification(manager,mqtt_manager, anchors, log_file_path):

    health_report_parser = HrParser()

    def handler(name, params):
        global new_burst
        global first_burst
        global burst_max_rssi
        global burst_closest_neighbor
        global position
        ts = datetime.datetime.now()
        with open(log_file_path, 'a') as f:
            log = {
                'type': name,
                'timestamp': time.ctime(),
                'params': params._asdict()
            }
            if 'macAddress' in log['params']:
                # convert the MAC address in 'params' to a human-friendly format
                # [0, 255, 0, 10, 0, 0, 0, 1] -> 00-ff-00-0a-00-00-00-01
                mac_address_in_list = log['params']['macAddress']
                log['params']['macAddress'] = (
                    '-'.join(map(lambda x: '%02x' % x, mac_address_in_list))
                )
            if it_is_blink_packet_log(log):
                parsed_data,burst_id = parse_blink_packet(manager, anchors, log)
                global current_burst_id
                print parsed_data
                log['parsed_data'] = parsed_data
                if (burst_id==current_burst_id):
                    print 'old burst'
                    new_burst=False
                else:
                    print 'new burst'
                    new_burst=True
                    current_burst_id=burst_id
                        
                if new_burst:
                    print 'first burst?'
                    if first_burst:
                        #do nothing
                        print 'first burst'
                        first_burst= False
                    else:
                        print 'later burst'
                        #Add the first neighbor
                        burst_max_rssi = parsed_data ['closest_neighbor']['rssi']
                        burst_closest_neighbor = { 
                           'macAddress': parsed_data ['closest_neighbor'] ['macAddress'],
                           'location': parsed_data ['closest_neighbor'] ['location'],
                           'rssi': parsed_data ['closest_neighbor'] ['rssi']
                           }
                        position = {
                        'type': 'tag-position',
                        'timestamp': ts.strftime('%c'),
                        'tag': tag['macAddress'],
                        'anchor': parsed_data ['closest_neighbor'] ['macAddress']
                        }
                        print '>>>>> sending last estimation<<<<<<<<<<'
                        print('publish position: {}'.format(position))
                        # send closest neighbor alreay selected from previous burst
                        mqtt_manager._send_blink_update(position)                        
                                           
                    print 'first neighbor'
                    print parsed_data ['closest_neighbor']
                    new_burst = False
                else:
                    print 'same burst'
                    # If found a closer neighbor, record it. 
                    print 'candidate rssi'
                    print parsed_data ['closest_neighbor']['rssi']
                    print 'closest rssi'
                    print burst_max_rssi
                    if (int((parsed_data ['closest_neighbor']['rssi'])>int(burst_max_rssi))):
                        print 'candidate greater left'
                    else:
                        print 'existing greater right'
                    if (int(parsed_data ['closest_neighbor']['rssi'])>int(burst_max_rssi)):
                        print 'found closer neighbor'
                        print parsed_data ['closest_neighbor']
                        #Add the  neighbor
                        burst_max_rssi = parsed_data ['closest_neighbor']['rssi']
                        burst_closest_neighbor = { 
                           'macAddress': parsed_data ['closest_neighbor'] ['macAddress'],
                           'location': parsed_data ['closest_neighbor'] ['location'],
                           'rssi': parsed_data ['closest_neighbor'] ['rssi']
                        }
                        position = {'type': 'tag-position',
                        'timestamp': ts.strftime('%c'),
                        'tag': tag['macAddress'],
                        'anchor': parsed_data ['closest_neighbor'] ['macAddress']
                        }                
                    #testing only
                    #print '>>>>> sending estimation<<<<<<<<<<'
                    #print('publish position: {}'.format(position))
                    # send closest neighbor alreay selected from previous burst
                    #mqtt_manager._send_blink_update(position)
            elif log['type'] == IpMgrSubscribe.NOTIFHEALTHREPORT:
                log['parsed_data'] = parse_health_report_packet(
                    manager,
                    health_report_parser,
                    log
                )
            else:
                # parsed_data is not added for a log comming here. if
                # we need temperature reports for localization, use
                # the result object returned by parse_oap_notif()
                # defined in SmartMeshSDK.protocols.oap.OAPNotif
                pass

            f.write('{}\n'.format(json.dumps(log)))

    spinner = Halo(text='Setting up Subscriber')
    spinner.start()

    try:
        subscriber = IpMgrSubscribe(manager)
        subscriber.start()
        subscriber.subscribe(
            notifTypes = IpMgrSubscribe.ALLNOTIF,
            fun        = handler,
            isRlbl     = False,
        )
    except IpMgrSubscribe.SubscribeError:
        spinner.fail()
        sys.exit('Failed to set up a subscriber.')

    spinner.succeed('Subscriber is ready.')

    

@click.command()
@click.argument('serial_dev')
@click.option('--acl-setup/--no-acl-setup', default=False,
              show_default=True,
              help='specify --acl-setup if ACL needs to be configured')
def main(serial_dev, acl_setup):

    manager = connect_manager(serial_dev)
    config = utils.load_config()
    log_file_path = prepare_log_file()

    if acl_setup:
        setup_acl(manager, config)

    anchors = {entry[0]: entry[1] for entry in [config.manager]+config.anchors}
    
    # This is where the MQTT connector will be initialized
    mqtt_manager = MqttManager()
    
    mqtt_manager.connect()
    subscribe_notification(manager, mqtt_manager, anchors, log_file_path)

    while True:
        if raw_input('Input "quit" to stop the script: ') == 'quit':
            print 'stopping...'
            break
        else:
            continue
    manager.disconnect()

if __name__ == '__main__':
    main()
