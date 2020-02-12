#!/usr/bin/env python

import os
import sys
import time

import click
from halo import Halo

import utils

sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
import SmartMeshSDK.ApiException
from SmartMeshSDK.IpMoteConnector import IpMoteConnector

BLINK_TIMEOUT_SECONDS = 120
RESET_WAIT_SECONDS = 10
NUM_BLINK_PACKETS_TO_SEND = 25
NUM_NEIGHBORS_IN_BLINK_PACKET = 4

def _print(str):
    sys.stdout.write(str)
    sys.stdout.flush()

def send_blink_packet(tag, payload, include_neighbors=True, with_reset=False):
    payload = map(lambda c: ord(c), list(payload))

    if include_neighbors:
        fIncludeDscvNbrs = NUM_NEIGHBORS_IN_BLINK_PACKET
    else:
        fIncludeDscvNbrs = 0

    if with_reset:
        reset(tag)
    else:
        # do nothing
        pass
    now = time.time()
    tag.dn_blink(fIncludeDscvNbrs, payload)
    notification = tag.getNotificationInternal(BLINK_TIMEOUT_SECONDS)
    time_delta = time.time() - now

    if (
        notification
        and
        notification[0] == ['txDone']
    ):
        # a blink packet is sent
        pass
    else:
        msg = (
            'No network around the tag?\n' +
            'Check if the manager and the anchors are running as expected'
        )
        raise RuntimeError(msg)

    return time_delta

def connect_tag(serial_dev):
    # prepaer and return a ready-to-use IpMoteConnector()
    spinner = Halo(text='Connecting to Tag')
    spinner.start()

    tag = IpMoteConnector.IpMoteConnector()

    try:
        tag.connect({'port': serial_dev})
    except SmartMeshSDK.ApiException.ConnectionError:
        spinner.fail()
        msg = (
            'Cannot establish connection to {}.\n'.format(serial_dev) +
            'Is this the right port for "API" of the tag?\n' +
            'You may have specified the port for "CLI".\n'
        )
        sys.exit(msg)

    spinner.succeed('Connected to Tag')
    return tag

def reset(tag):
    # clear a pending blink packet by reset if any
    spinner = Halo(text='Resetting Tag')
    spinner.start()

    # clear notification queue
    while tag.getNotificationInternal(timeoutSec=1) != None:
        # timeoutSec needs to be equal to or larger than one to get a
        # remaining notification from the tag.
        pass

    # issue the reset command
    try:
        res = tag.dn_reset()
        assert res.RC == 0 # RC_OK
    except SmartMeshSDK.ApiException.ConnectionError as err:
        spinner.fail()
        msg = (
            'Is the tag powered?\n' +
            'Make sure the tag is running under the Slave mode.\n' +
            'Access the tag via CLI port, then:\n' +
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
        notification = tag.getNotificationInternal(timeoutSec=1)
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

    spinner.succeed('Tag is ready')

def test_blink(tag):
    spinner = Halo(text='Testing Blink')
    spinner.start()

    try:
        # test Blink
        send_blink_packet(tag, payload='test', include_neighbors=False)
    except (RuntimeError, SmartMeshSDK.ApiException.ConnectionError) as err:
        spinner.fail()
        sys.exit('Failed to send a Blink packet: {}'.format(err))

    spinner.succeed('Blink works fine')
    return tag

@click.command()
@click.argument('serial_dev')
@click.option('--num-packets', default=NUM_BLINK_PACKETS_TO_SEND,
              show_default=True,
              help='number of blink packets to send for one measurement')
@click.option('--profile-mode/--no-profile-mode', default=False,
              show_default=True,
              help=('send blink packets without user input, ' +
                    'and print process time for each Blink')
              )
@click.option('--with-reset/--without-reset', default=False,
              show_default=True,
              help=('reset before issuing a blink command')
              )
def main(serial_dev, num_packets, profile_mode, with_reset):
    tag = connect_tag(serial_dev)

    if profile_mode:
        log_file_path = os.path.join(
            utils.get_blink_base_path(),
            'blink-process-time-data.txt'
        )
        if os.path.exists(log_file_path):
            msg = ('{} exists; '.format(log_file_path) +
                   'rename it, then retry the script')
            raise EnvironmentError(msg)
        else:
            open(log_file_path, 'w').close()
            print ('process time of Blink command will '+
                   'be written into {}'.format(log_file_path))
            print '{} blink packets will be sent'.format(num_packets)
        str = 'profile'
        if (with_reset):
            reset(tag)
        test_blink(tag)
        print 'Measurement started'
        for _ in range(num_packets):
            time_delta = send_blink_packet(
                tag,
                payload=str,
                include_neighbors=True,
                with_reset=with_reset
            )
            with open(log_file_path, 'a') as f:
                 f.write('{}\n'.format(time_delta))
                 f.flush()
        print 'Measurement done'
    else:
        if (with_reset):
            reset(tag)
        test_blink(tag)
        msg = 'Input something to send or "quit" to stop this script: '
        while True:
            str = raw_input(msg)

            if not str:
                continue
            elif str == 'quit':
                print 'stopping...'
                break
            else:
                _print('Sending blink packets with "{}": '.format(str))
                now = time.time()
                for _ in range(num_packets):
                    send_blink_packet(
                        tag,
                        payload=str,
                        include_neighbors=True,
                        with_reset=with_reset
                    )
                    _print('.')
                _print(' [done, {}s]'.format(int(time.time() - now)))
                _print('\n')

    tag.disconnect()

if __name__ == '__main__':
    main()
