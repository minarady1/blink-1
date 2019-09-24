#!/bin/sh
echo "genereate deployment.png"
python ./draw.py -o results/deployment.png

echo "analyzer.py"
./analyzer.py measurements/log-blink-manager-0919.jsonl

echo "plot_otii_csv.py"
./plot_otii_csv.py measurements/otti-blink.csv

echo "plot_blink_command_profile.py"
./plot_blink_command_profile.py measurements/blink-command
