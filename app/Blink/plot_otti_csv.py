#!/usr/bin/env python

import os

import click
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import utils

LOWER_XLIM = 3.75
HIGHER_XLIM = 8.50

@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
def main(csv_file):
    output_file_path = os.path.join(
        utils.get_blink_base_path(),
        'results',
        'chart-tag-current-over-time.png'
    )
    df = pd.read_csv(
        csv_file,
        delimiter = ',',
        dtype     = 'float',
        names     = ['timestamp', 'current', 'voltage', 'energy'],
        skiprows  = [0]
    )
    df['current'] = df['current'] * 1000 # convert A to mA
    df['timestamp'] -= LOWER_XLIM
    higher_xlim = HIGHER_XLIM - LOWER_XLIM

    plt.figure()
    g = sns.lineplot(
        x    = 'timestamp',
        y    = 'current',
        data = df[(df['timestamp']>=0) & (df['timestamp']<=higher_xlim)]
    )
    g.set(
        xlabel = 'Time (s)',
        ylabel = 'Current (mA)'
    )
    plt.savefig(output_file_path)
    plt.close()

if __name__ == '__main__':
   main()
