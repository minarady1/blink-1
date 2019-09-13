#!/usr/bin/env python

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
from SmartMeshSDK.IpMgrConnectorMux     import IpMgrSubscribe
from SmartMeshSDK.protocols.blink.blink import decode_blink

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
    # - add an ACL entry for the sensor
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
    mote_list = [config.sensor] + config.anchors
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

def subscribe_notification(manager, log_file_path):
    def handler(name, params):
        params = params._asdict()
        with open(log_file_path, 'a') as f:
            log = {'name': name, 'params': params}
            f.write('{}\n'.format(json.dumps(log)))

        # if it is about a blink packet, print it
        if (
            name == 'notifData'
            and
            'data' in params
            and
            params['data'][0] == BLINK_PAYLOAD_COMMAND_ID
        ):
            payload = ''.join([chr(b) for b in params['data']])
            data, neighbors = decode_blink(payload)
            print '{}: '.format(data)

            if neighbors:
                for id, rssi in neighbors:
                    print 'o id: {0}, rssi: {1}'.format(id, rssi)
            else:
                pass

    spinner = Halo(text='Setting up Subscriber')
    spinner.start()

    try:
        subscriber = IpMgrSubscribe.IpMgrSubscribe(manager)
        subscriber.start()
        subscriber.subscribe(
            notifTypes = IpMgrSubscribe.IpMgrSubscribe.ALLNOTIF,
            fun        = handler,
            isRlbl     = False,
        )
    except IpMgrSubscribe.SubscribeError:
        spinner.fail()
        sys.exit('Failed to set up a subscriber.')

    spinner.succeed('Subscriber is ready.')

@click.command()
@click.argument('serial_dev')
def main(serial_dev):
    manager = connect_manager(serial_dev)
    config = load_config()
    log_file_path = prepare_log_file()

    setup_acl(manager, config)
    subscribe_notification(manager, log_file_path)

    while True:
        if raw_input('Input "quit" to stop the script: ') == 'quit':
            print 'stoping...'
            break
        else:
            continue
    manager.disconnect()

if __name__ == '__main__':
    main()
