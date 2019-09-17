#!/usr/bin/env python

from array import array
from collections import namedtuple
import json
import os
import sys
import time

import click
from halo import Halo

sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
import SmartMeshSDK.ApiException
from SmartMeshSDK.IpMgrConnectorSerial import IpMgrConnectorSerial
from SmartMeshSDK.IpMgrConnectorMux.IpMgrSubscribe import IpMgrSubscribe
from SmartMeshSDK.protocols.Hr.HrParser import HrParser
from SmartMeshSDK.protocols.blink import blink

BLINK_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_NAME = 'config.json'
LOG_DIR_NAME = 'logs'
# See "Factory Default Settings", Section 3.7 of SmartMesh IP User's Guide
DEFAULT_JOIN_KEY = (
    0x44, 0x55, 0x53, 0x54, 0x4E, 0x45, 0x54, 0x57,
    0x4F, 0x52, 0x4B, 0x53, 0x52, 0x4F, 0x43, 0x4B
)
# See libs/SmartMeshSDK/protocols/blink/blink.py
BLINK_PAYLOAD_COMMAND_ID = 0x94

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

def load_config():
    # load config.json, and convert a resulting dict to a namedtuple
    # so that we can access config parameters as attributes, like
    # config.anchors instead of config['anchors'].
    spinner = Halo(text='Loading config')
    spinner.start()

    config_path = os.path.join(BLINK_BASE_PATH, CONFIG_FILE_NAME)

    try:
        with open(config_path) as f:
            config = json.load(
                f,
                object_hook = (
                    lambda d: namedtuple('Config', d.keys())(*d.values())
                )
            )
    except IOError:
        spinner.fail()
        msg = (
            'Cannot load the config file.\n' +
            'Confirm that {} exists and is readable.'.format(config_path)
        )
        sys.exit(msg)

    spinner.succeed('Config is loaded')
    return config

def prepare_log_file():
    spinner = Halo(text='Preparing a log file')
    log_dir_path = os.path.join(BLINK_BASE_PATH, LOG_DIR_NAME)

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

def parse_blink_packet(manager, anchors, log):
    payload = ''.join([chr(b) for b in log['params']['data']])
    user_input, neighbors = blink.decode_blink(payload)

    new_neighbors = []
    for mote_id, rssi in neighbors:
        mac_addr = convert_mote_id_to_mac_address(manager, mote_id)
        new_neighbors.append({
            'macAddress': mac_addr,
            'location': get_anchor_location(anchors, mac_addr),
            'rssi': rssi
        })

    for neighbor in new_neighbors:
        print neighbor
    print '---'

    return {
        'subtype': 'blink',
        'user_input': user_input,
        'neighbors': new_neighbors
    }

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

def subscribe_notification(manager, anchors, log_file_path):
    health_report_parser = HrParser()

    def handler(name, params):
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
                log['parsed_data'] = parse_blink_packet(manager, anchors, log)
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
    config = load_config()
    log_file_path = prepare_log_file()

    if acl_setup:
        setup_acl(manager, config)

    anchors = {entry[0]: entry[1] for entry in [config.manager]+config.anchors}
    subscribe_notification(manager, anchors, log_file_path)

    while True:
        if raw_input('Input "quit" to stop the script: ') == 'quit':
            print 'stoping...'
            break
        else:
            continue
    manager.disconnect()

if __name__ == '__main__':
    main()
