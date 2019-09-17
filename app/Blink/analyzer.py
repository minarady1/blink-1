#!/usr/bin/env python

from array import array
import json
import os
import sys
import time

import click
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
from SmartMeshSDK.IpMgrConnectorMux.IpMgrSubscribe import IpMgrSubscribe

def analyze(blink_logs):
    df = pd.DataFrame(columns=['ground_truth', 'neighbor', 'rssi'])

    for log in blink_logs:
        parsed_data = log['parsed_data']
        for neighbor in parsed_data['neighbors']:
            df = df.append(
                {
                    'ground_truth': parsed_data['user_input'],
                    'neighbor'    : neighbor['location'],
                    'rssi'        : neighbor['rssi'],
                    'log_seqno'   : log['seqno']
                },
                ignore_index=True
            )
    df['rssi'] = pd.to_numeric(df['rssi'])
    df['log_seqno'] = pd.to_numeric(df['log_seqno'])

    for ground_truth in df.ground_truth.unique():
        #print df.ground_truth.unique()
        plt.figure()
        g = sns.boxplot(
            x    = 'neighbor',
            y    = 'rssi',
            data = df[df['ground_truth']==ground_truth]
        )
        plt.xticks(rotation=30)
        plt.savefig('{}-rssi-vs-neighbor.png'.format(ground_truth))
        plt.close()

    plt.figure()
    g = sns.boxplot(
        y    = 'log_seqno',
        data = pd.pivot_table(
            df[df['neighbor']==df['ground_truth']],
            values  = 'log_seqno',
            index   = 'ground_truth',
            aggfunc = np.min
        )
    )
    plt.savefig('num_packets_to_get_closest_anchor.png')
    plt.close()

@click.command()
@click.argument('log_file_path', type=click.File('r'))
def main(log_file_path):
    last_ground_truth = None
    seqno = 0
    blink_logs = []
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
            if last_ground_truth == log['parsed_data']['user_input']:
                seqno += 1
            else:
                last_ground_truth = log['parsed_data']['user_input']
                seqno = 0
            log['seqno'] = seqno
            blink_logs.append(log)
        elif log['type'] == IpMgrSubscribe.NOTIFHEALTHREPORT:
            pass

    analyze(blink_logs)

if __name__ == '__main__':
    main()
