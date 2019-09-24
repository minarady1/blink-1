#!/bin/sh
echo "genereate deployment.png"
python ./draw.py -o results/deployment.png

echo "analyzer.py"
./analyzer.py measurements/log-blink-manager-20190919-143138.jsonl

echo "plot_otti_csv.py"
./plot_otti_csv.py measurements/blink_1.csv

echo "plot_blink_command_profile.py"
./plot_blink_command_profile.py measurements/blink-command
