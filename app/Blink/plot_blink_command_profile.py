#!/usr/bin/env python

from glob import glob
from collections import namedtuple
import json
import os

import click
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

import utils

BLINK_PROCESS_TIME_LOG_FILENAME = 'blink-process-time-data.txt'
MANAGER_LOG_FILE_PREFIX = 'log-blink-manager'
RESULT_DIR_NAME = 'results'

def generate_chart_blink_process_time(logs):
    data = pd.DataFrame()
    for log in logs:
        df = pd.read_csv(log.tag_log, header=None, names=['time'])
        df['num_neighbors'] = log.num_neighbors
        if data.empty:
            data = df
        else:
            data = data.append(df, ignore_index=True)

    data = data.astype({'time': float, 'num_neighbors': int})

    for plot_type in ['boxplot', 'lineplot']:
        output_file_path = os.path.join(
            RESULT_DIR_NAME,
            'chart-blink-process-time-{}.png'.format(plot_type)
        )
        plt.figure()
        if plot_type == 'boxplot':
            g = sns.boxplot(
                x     = 'num_neighbors',
                y     = 'time',
                color = 'skyblue',
                data  = data,
                order = np.arange(31)
            )
        elif plot_type == 'lineplot':
            g = sns.lineplot(
                x         = 'num_neighbors',
                y         = 'time',
                ci        = 95,
                err_style = 'bars',
                data      = data
            )
        else:
            raise NotImplemented()

        g.set(
            xlabel = 'number of neighbors',
            ylabel = 'processing time of Blink command (s)'
        )
        plt.savefig(output_file_path)
        plt.close()

def genreate_chart_discovered_neighbor(logs):
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-num_discovered-vs-num_packets.png'
    )
    data = pd.DataFrame()

    for log in logs:
        num_packets = 0
        num_discovered_hist = []
        global_mac_addr_set = set()
        with open(log.manager_log, 'r') as f:
            for line in f:
                log_line = json.loads(line)
                if (
                        utils.it_is_blink_log(log_line)
                        and
                        log_line['parsed_data']['user_input'] != 'test'
                ):
                    num_packets += 1
                    mac_addr_list = [
                        neighbor['macAddress']
                        for neighbor in log_line['parsed_data']['neighbors']
                    ]
                    #for mac_addr in mac_addr_list:
                    #    print mac_addr
                    global_mac_addr_set = global_mac_addr_set.union(
                        set(mac_addr_list)
                    )
                    num_discovered_hist.append(len(global_mac_addr_set))
                else:
                    # skip this one
                    pass
        df = pd.DataFrame(
            {
                'num_packets': np.arange(num_packets),
                'num_discovered': num_discovered_hist
            }
        )
        df['num_neighbors'] = int(log.num_neighbors)

        if data.empty:
            data = df
        else:
            data = data.append(df, ignore_index=True)

    plt.figure()
    sns.set_context('paper')
    g = sns.pointplot(
        x         = 'num_packets',
        y         = 'num_discovered',
        hue       = 'num_neighbors',
        data      = data[data['num_packets']<=90],
        hue_order = sorted(
            data['num_neighbors'].unique().tolist(),
            reverse=True
        ),
        scale     = 0.5
    )
    g.set(
        xlabel = 'number of Blink packets',
        ylabel = 'number of discovered unique neighbors'
    )
    g.xaxis.set_major_locator(ticker.MultipleLocator(10))
    g.xaxis.set_major_formatter(ticker.ScalarFormatter())
    plt.savefig(output_file_path)
    plt.close()

@click.command()
@click.argument('log_dir', type=click.Path(exists=True))
def main(log_dir):
    subdir_pattern = os.path.join(log_dir, '*-neighbor*')
    LogFile = namedtuple('LogFile', ['num_neighbors', 'tag_log', 'manager_log'])
    logs = []
    for subdir in glob(subdir_pattern):
        num_neighbors = os.path.basename(subdir).split('-')[0]
        for filepath in glob(os.path.join(subdir, '*')):
            if os.path.basename(filepath) == BLINK_PROCESS_TIME_LOG_FILENAME:
                tag_log = filepath
            elif os.path.basename(filepath).startswith(MANAGER_LOG_FILE_PREFIX):
                manager_log = filepath
        assert tag_log
        assert manager_log
        logs.append(LogFile(num_neighbors, tag_log, manager_log))

    genreate_chart_discovered_neighbor(logs)
    generate_chart_blink_process_time(logs)

if __name__ == '__main__':
    main()
