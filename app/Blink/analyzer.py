#!/usr/bin/env python

from array import array
import json
import math
import os
import sys
import time

import click
from halo import Halo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs'))
from SmartMeshSDK.IpMgrConnectorMux.IpMgrSubscribe import IpMgrSubscribe

from draw import draw_floor_map
import utils

RESULT_DIR_NAME = 'results'
NUM_BLINK_PACKETS = 25

def get_weight(rssi):
    POSSIBLE_BEST_RSSI = -35.0
    POSSIBLE_WORST_RSSI = -60.0
    if rssi > POSSIBLE_BEST_RSSI:
        weight = 1
    elif rssi < POSSIBLE_WORST_RSSI:
        weight = 0
    else:
        weight = POSSIBLE_BEST_RSSI / rssi
    return weight

def compute_tag_position_with_weighted_average(anchor_position_list, data):
    data = pd.pivot_table(
        data,
        values   = 'rssi',
        index   = 'anchor',
        aggfunc = np.max
    )
    weight_list = [get_weight(row.rssi) for _, row in data.iterrows()]
    # compute weighted coordinates of each anchor
    coord_list = map(
        lambda coord: (coord[0][0] * coord[1], coord[0][1] * coord[1]),
        [
            (anchor_position_list[anchor_mac_addr], weight)
            for anchor_mac_addr, weight in zip(data.index.tolist(), weight_list)
        ]
    )
    # remove coordents of (0, 0)
    coord_list = [coord for coord in coord_list if coord != (0, 0)]

    # average the weighted coordinates
    if coord_list:
        x = sum([coord[0] for coord in coord_list]) / len(coord_list)
        y = sum([coord[1] for coord in coord_list]) / len(coord_list)
    else:
        x = None
        y = None

    return x, y

def get_anchor_position_list(config):
    anchor_position_list = {}
    for anchor in config.anchors:
        if len(anchor) > 2:
            anchor_position_list[anchor[0]] = anchor[2]
        else:
            pass
    return anchor_position_list

def generate_chart_error_vs_num_packet(ground_truth, error_list):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-error-vs-num_packet-{}.png'.format(ground_truth)
    )
    df = pd.DataFrame(
        data = {
            'num_packet': [i+1 for i in range(len(error_list))],
            'error'     : error_list
        },
        dtype = int
    )
    plt.figure()
    sns.pointplot(
        x    = 'num_packet',
        y    = 'error',
        data = df
    )
    plt.savefig(output_file_path)
    plt.close()

def generate_map_tag_position_by_weighted_average(
        config,
        ground_truth,
        data):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'map-tag_position-by-weighted_average-{}.png'.format(ground_truth)
    )

    for anchor in config.anchors:
        if anchor[1] == ground_truth:
            closest_anchor_position = anchor[2]
            break
    error_list = []
    for i in range(NUM_BLINK_PACKETS):
        tag_position = compute_tag_position_with_weighted_average(
            get_anchor_position_list(config),
            data[data['log_seqno']<=i]
        )
        if tag_position[0]:
            error_list.append(
                math.sqrt(
                    (tag_position[0]-closest_anchor_position[0])**2 +
                    (tag_position[1]-closest_anchor_position[1])**2
                )
            )
        else:
            error_list.append(None)

    df_max_rssi = pd.pivot_table(
        data,
        values  = 'rssi',
        index   = 'anchor',
        aggfunc = np.max
    )
    max_rssi_list = df_max_rssi.to_dict()['rssi']

    draw_floor_map(
        config,
        output_file_path,
        ground_truth,
        tag_position,
        max_rssi_list
    )
    generate_chart_error_vs_num_packet(ground_truth, error_list)

def generate_chart_rssi_vs_anchor_location(ground_truth, data):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-rssi-vs-anchor_location-{}.png'.format(ground_truth)
    )
    plt.figure()
    g = sns.boxplot(
        x    = 'anchor_location',
        y    = 'rssi',
        data = data
    )
    plt.xticks(rotation=30)
    plt.savefig(output_file_path)
    plt.close()

def generate_chart_num_packets_to_get_closest_anchor(df):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-num_packets_to_get_closest_anchor.png'
    )
    plt.figure()
    g = sns.boxplot(
        y    = 'log_seqno',
        data = pd.pivot_table(
            df[df['anchor_location']==df['ground_truth']],
            values  = 'log_seqno',
            index   = 'ground_truth',
            aggfunc = np.min
        )
    )
    plt.savefig(output_file_path)
    plt.close()

def prepare_dataframe(config, blink_logs):
    spinner = Halo(text='Preparing a DataFrame object for analysis')
    spinner.start()

    df = pd.DataFrame(columns=[
        'ground_truth',
        'anchor',
        'anchor_location',
        'rssi'
    ])

    for log in blink_logs:
        parsed_data = log['parsed_data']
        for neighbor in parsed_data['neighbors']:
            if neighbor['macAddress'] == config.manager[0]:
                # ignore a RSSI value from the manager
                pass
            else:
                df = df.append(
                    {
                        'ground_truth'   : parsed_data['user_input'],
                        'anchor'         : neighbor['macAddress'],
                        'anchor_location': neighbor['location'],
                        'rssi'           : neighbor['rssi'],
                        'log_seqno'      : log['seqno']
                    },
                    ignore_index=True
                )
    df['rssi'] = pd.to_numeric(df['rssi'])
    df['log_seqno'] = pd.to_numeric(df['log_seqno'])

    spinner.succeed('The DataFrame object is ready')
    return df

def load_blink_logs(log_file):
    last_ground_truth = None
    seqno = 0
    blink_logs = []
    for line in log_file:
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
    return blink_logs

def prepare_result_directory():
    spinner = Halo(text='Preparing the directory for results')
    spinner.start()

    result_dir_path = os.path.join(utils.get_blink_base_path(), RESULT_DIR_NAME)
    # make sure we have the log directory
    if os.path.isdir(result_dir_path):
        pass
    else:
        try:
            os.mkdir(result_dir_path)
        except OSError as err:
            spinner.fail()
            sys.exit('Failed to make the directory for results: {}'.format(err))

    spinner.succeed('The directory for results is ready')

@click.command()
@click.argument('log_file', type=click.File('r'))
def main(log_file):
    prepare_result_directory()

    config = utils.load_config()
    blink_logs = load_blink_logs(log_file)
    df = prepare_dataframe(config, blink_logs)

    spinner = Halo(text='Analyzing...')
    spinner.start()

    for ground_truth in df.ground_truth.unique():
        data = df[df['ground_truth']==ground_truth]
        generate_chart_rssi_vs_anchor_location(ground_truth, data)
        generate_map_tag_position_by_weighted_average(
            config,
            ground_truth,
            data
        )

    generate_chart_num_packets_to_get_closest_anchor(df)

    spinner.succeed('Done')

if __name__ == '__main__':
    main()
