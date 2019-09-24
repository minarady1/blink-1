#!/usr/bin/env python

import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

from analyzer import (
    get_room_error_list,
    load_blink_logs,
    prepare_dataframe
)
import utils

RESULT_DIR_NAME = 'results'
LOG_DIR_PATH = 'measurements'
LOG_FILES = [
    'log-blink-manager-0917.jsonl',
    'log-blink-manager-0919.jsonl'
]

def main():
    output_file_path = os.path.join(
        RESULT_DIR_NAME,
        'chart-accuracy_distribution-with-all-datasets.png'
    )

    config = utils.load_config()
    data = pd.DataFrame()
    num_measurements = 0

    for log_file in LOG_FILES:
        log_file_path = os.path.join(LOG_DIR_PATH, log_file)
        with open(log_file_path, 'r') as f:
            blink_logs = load_blink_logs(f)
            df = prepare_dataframe(config, blink_logs)

        num_measurements += len(df.ground_truth.unique())
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
    data['accuracy'] = data['accuracy'] / num_measurements * 100

    plt.figure()
    sns.set_context('paper')
    sns.set_style('whitegrid')
    g = sns.lineplot(
        x    = 'num_packets',
        y    = 'accuracy',
        data = data,
        lw   = 2
    )
    g.set(
        xlabel = 'number of Blink packets',
        ylabel = 'accuracy rate (%)',
        xlim   = (1, 25),
        ylim   = (0, 100),
    )
    g.xaxis.set_major_locator(ticker.MultipleLocator(1))
    g.xaxis.set_major_formatter(ticker.ScalarFormatter())
    g.yaxis.set_major_locator(ticker.MultipleLocator(10))
    g.yaxis.set_major_formatter(ticker.ScalarFormatter())
    plt.savefig(output_file_path)
    plt.close()

if __name__ == '__main__':
    main()
