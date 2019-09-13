#!/usr/bin/env python

import os
import sys
import time

import click
from halo import Halo

sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
import SmartMeshSDK.ApiException
from SmartMeshSDK.IpMoteConnector import IpMoteConnector

BLINK_TIMEOUT_SECONDS = 65
RESET_WAIT_SECONDS = 10
NUM_BLINK_PACKETS_TO_SEND = 10
NUM_NEIGHBORS_IN_BLINK_PACKET = 4

def _print(str):
    sys.stdout.write(str)
    sys.stdout.flush()

def send_blink_packet(sensor, payload, include_neighbors=True):
    payload = map(lambda c: ord(c), list(payload))

    if include_neighbors:
        fIncludeDscvNbrs = NUM_NEIGHBORS_IN_BLINK_PACKET
    else:
        fIncludeDscvNbrs = 0

    sensor.dn_blink(fIncludeDscvNbrs, payload)
    notification = sensor.getNotificationInternal(BLINK_TIMEOUT_SECONDS)
    if (
        notification
        and
        notification[0] == ['txDone']
    ):
        # a blink packet is sent
        pass
    else:
        msg = (
            'No network around the sensor?\n' +
            'Check if the manager and the anchors are running as expected'
        )
        raise RuntimeError(msg)

def connect_sensor(serial_dev):
    # prepaer and return a ready-to-use IpMoteConnector()
    spinner = Halo(text='Connecting to Sensor')
    spinner.start()

    sensor = IpMoteConnector.IpMoteConnector()

    try:
        sensor.connect({'port': serial_dev})
    except SmartMeshSDK.ApiException.ConnectionError:
        spinner.fail()
        msg = (
            'Cannot establish connection to {}.\n'.format(serial_dev) +
            'Is this the right port for "API" of the sensor?\n' +
            'You may have specified the port for "CLI".\n'
        )
        sys.exit(msg)

    spinner.succeed('Connected to Sensor')
    return sensor

def reset(sensor):
    # clear a pending blink packet by reset if any
    spinner = Halo(text='Resetting Sensor')
    spinner.start()

    # clear notification queue
    while sensor.getNotificationInternal(timeoutSec=1) != None:
        # timeoutSec needs to be equal to or larger than one to get a
        # remaining notification from the sensor.
        pass

    # issue the reset command
    try:
        res = sensor.dn_reset()
        assert res.RC == 0 # RC_OK
    except SmartMeshSDK.ApiException.ConnectionError as err:
        spinner.fail()
        msg = (
            'Is the sensor powered?\n' +
            'Make sure the sensor is running under the Slave mode.\n' +
            'Access the sensor via CLI port, then:\n' +
            '\n' +
            ' > get mode\n' +
            '\n'
            'If you get "master", change the mode to "slave"\n' +
            '\n' +
            '  > set mode slave\n' +
            '  > reset'
        )
        sys.exit(msg)

    # wait until it boots
    start_time = time.time()
    while True:
        notification = sensor.getNotificationInternal(timeoutSec=1)
        if (
                notification
                and
                notification[0] == ['events']
                and
                notification[1]['events'] == 1 # boot
                and
                notification[1]['state'] == 1 # join
        ):
            # booted after reset
            break
        elif (time.time() - start_time) < RESET_WAIT_SECONDS:
            continue
        elif time.time() < start_time:
            # clock was changed to the past
            spinner.fail()
            sys.exit('unexpected error; negative time difference')
        else:
            spinner.fail()
            sys.exit('reset do not complete in time')

    spinner.succeed('Sensor is ready')

def test_blink(sensor):
    spinner = Halo(text='Testing Blink')
    spinner.start()

    try:
        # test Blink
        send_blink_packet(sensor, payload='test', include_neighbors=False)
    except (RuntimeError, SmartMeshSDK.ApiException.ConnectionError) as err:
        spinner.fail()
        sys.exit('Failed to send a Blink packet: {}'.format(err))

    spinner.succeed('Blink works fine')
    return sensor

@click.command()
@click.argument('serial_dev')
def main(serial_dev):
    sensor = connect_sensor(serial_dev)

    reset(sensor)
    test_blink(sensor)

    msg = 'Input something to send or "quit" to stop this script: '
    while True:
        str = raw_input(msg)
        if not str:
            continue
        elif str == 'quit':
            print 'stoping...'
            break
        else:
            _print('Sending blink packets with "{}": '.format(str))
            for _ in range(NUM_BLINK_PACKETS_TO_SEND):
                send_blink_packet(sensor, payload=str)
                _print('.')
            _print('\n')

    sensor.disconnect()

if __name__ == '__main__':
    main()
