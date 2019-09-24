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

from draw import draw_floor_map
import utils

RESULT_DIR_NAME = 'results'
NUM_BLINK_PACKETS = 25
METER_PER_PIXEL = 0.057

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

def compute_tag_position_by_weighted_average(anchor_position_list, data):
    data = pd.pivot_table(
        data,
        values  = 'rssi',
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

def compute_tag_position_by_strongest_rssi(data):
    df_max_rssi = pd.pivot_table(
        data,
        values  = 'rssi',
        index   = 'anchor',
        aggfunc = np.max
    )

    if df_max_rssi.empty:
        location = None
        mac_addr = None
    else:
        max_rssi_list = df_max_rssi.to_dict()['rssi']
        closest_anchor = data[data['rssi']==data['rssi'].max()]
        location = closest_anchor.iloc[0]['anchor_location']
        mac_addr = closest_anchor.iloc[0]['anchor']

    return (mac_addr, location)

def get_anchor_position_list(config):
    anchor_position_list = {}
    for anchor in config.anchors:
        if len(anchor) > 2:
            anchor_position_list[anchor[0]] = anchor[2]
        else:
            pass
    return anchor_position_list

def get_position_error_list(config, data, ground_truth):
    for anchor in config.anchors:
        if anchor[1] == ground_truth:
            closest_anchor_position = anchor[2]
            break

    error_list = []
    for i in range(NUM_BLINK_PACKETS):
        tag_position = compute_tag_position_by_weighted_average(
            get_anchor_position_list(config),
            data[data['log_seqno']<=i]
        )
        if tag_position[0]:
            error_list.append(
                math.sqrt(
                    (tag_position[0]-closest_anchor_position[0])**2 +
                    (tag_position[1]-closest_anchor_position[1])**2
                )
                *
                METER_PER_PIXEL
            )
        else:
            error_list.append(np.nan)
    return error_list

def generate_chart_error_vs_num_packet(ground_truth, error_list):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-error-vs-num_packet-{}.png'.format(ground_truth)
    )
    df = pd.DataFrame(
        data = {
            'num_packets': [i+1 for i in range(len(error_list))],
            'error'     : error_list
        },
        dtype = int
    )
    plt.figure()
    g = sns.pointplot(
        x    = 'num_packets',
        y    = 'error',
        data = df
    )
    g.set(
        xlabel = 'number of Blink Packets',
        ylabel = 'error (m)'
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

    generate_chart_error_vs_num_packet(
        ground_truth,
        get_position_error_list(config, data, ground_truth)
    )

    df_max_rssi = pd.pivot_table(
        data,
        values  = 'rssi',
        index   = 'anchor',
        aggfunc = np.max
    )
    max_rssi_list = df_max_rssi.to_dict()['rssi']
    tag_position = compute_tag_position_by_weighted_average(
        get_anchor_position_list(config),
        data
    )

    draw_floor_map(
        config,
        output_file_path,
        ground_truth,
        tag_position,
        max_rssi_list
    )

def get_room_error_list(config, data, ground_truth):
    error_list = []
    for i in range(NUM_BLINK_PACKETS):
        _, tag_room = compute_tag_position_by_strongest_rssi(
            data[data['log_seqno']<=i]
        )
        error_list.append(1 if tag_room==ground_truth else 0)
    return error_list

def generate_map_tag_position_by_strongest_rssi(
        config,
        ground_truth,
        data):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'map-tag_position-by-strongest_rssi-{}.png'.format(ground_truth)
    )

    closest_anchor, closest_anchor_location = (
        compute_tag_position_by_strongest_rssi(data)
    )
    anchor_position_list = get_anchor_position_list(config)
    tag_position = anchor_position_list[closest_anchor]
    max_rssi_list = pd.pivot_table(
        data,
        values  = 'rssi',
        index   = 'anchor',
        aggfunc = np.max
    ).to_dict()['rssi']

    draw_floor_map(
        config,
        output_file_path,
        ground_truth,
        tag_position,
        max_rssi_list
    )

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
    g.set(
        xlabel = '',
        ylabel = 'RSSI (dBm)'
    )
    plt.savefig(output_file_path)
    plt.close()

def generate_chart_accuracy_distribution(config, df):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-accuracy_distribution'
    )
    data = pd.DataFrame()
    for ground_truth in df.ground_truth.unique():
        error_list = get_room_error_list(
            config,
            df[df['ground_truth']==ground_truth],
            ground_truth
        )
        data = data.append(
            pd.DataFrame(
                data = {
                    'num_packets': [i+1 for i in range(len(error_list))],
                    'accuracy'     : error_list
                },
                dtype = float
            ),
            ignore_index=True
        )
    data = pd.pivot_table(
        data,
        values  = 'accuracy',
        index   = 'num_packets',
        aggfunc = np.sum
    )
    data = data.reset_index()
    num_of_measurements = len(df.ground_truth.unique())
    data['accuracy'] = data['accuracy'] / num_of_measurements

    plt.figure()
    sns.set_context('paper')
    g = sns.lineplot(
        x     = 'num_packets',
        y     = 'accuracy',
        data  = data
    )
    g.set(
        xlabel = 'number of Blink packets',
        ylabel = 'probability',
        ylim = (0, 1.1)
    )
    plt.savefig(output_file_path)
    plt.close()

def generate_chart_error_distribution(config, df):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-error-distribution.png'
    )
    data = pd.DataFrame()
    for ground_truth in df.ground_truth.unique():
        error_list = get_position_error_list(
            config,
            df[df['ground_truth']==ground_truth],
            ground_truth
        )
        data = data.append(
            pd.DataFrame(
                data = {
                    'num_packets': [i+1 for i in range(len(error_list))],
                    'error'     : error_list
                },
                dtype = int
            ),
            ignore_index=True
        )
    data = data.astype({'error': float})

    plt.figure()
    g = sns.boxplot(
        x     = 'num_packets',
        y     = 'error',
        color = 'skyblue',
        data  = data
    )
    g.set(
        xlabel = 'number of Blink Packets',
        ylabel = 'error (m)'
    )
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
    g.set(
        xlabel = '',
        ylabel = 'number of Blink Packets'
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
        if utils.it_is_blink_log(log):
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

    generate_chart_accuracy_distribution(config, df) # room-level
    generate_chart_error_distribution(config, df)    # distance

    for ground_truth in df.ground_truth.unique():
        data = df[df['ground_truth']==ground_truth]
        generate_chart_rssi_vs_anchor_location(ground_truth, data)
        generate_map_tag_position_by_strongest_rssi(
            config,
            ground_truth,
            data
        )
        generate_map_tag_position_by_weighted_average(
            config,
            ground_truth,
            data
        )

    generate_chart_num_packets_to_get_closest_anchor(df)

    spinner.succeed('Done')

if __name__ == '__main__':
    main()
