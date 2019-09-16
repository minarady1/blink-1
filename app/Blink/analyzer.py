#!/usr/bin/env python

from array import array
import json
import os
import sys
import time

import click

sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
from SmartMeshSDK.IpMgrConnectorMux.IpMgrSubscribe import IpMgrSubscribe

@click.command()
@click.argument('log_file_path', type=click.File('r'))
def main(log_file_path):
    for line in log_file_path:
        log = json.loads(line)
        if (
            log['type'] == IpMgrSubscribe.NOTIFDATA
            and
            'parsed_data' in log
            and
            'subtype' in log['parsed_data']
            and
            log['parsed_data']['subtype'] == 'blink'
        ):
            print log
        elif log['type'] == IpMgrSubscribe.NOTIFHEALTHREPORT:
            print log

if __name__ == '__main__':
    main()
