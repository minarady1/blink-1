
# Blink

This directory is organized as follows:
- BlinkScript contains:
  - the python script that excutes the blink commands on the blink device and creates the experiment logs from the blink side. It allows tagging blink packets and logging sync time for each transaction
  - Sample Logs
- NetworkBenchmarkingScript: contains the script to measure impact of network size on transaction performance. 
- ManagerScript contains 
  - the python script that logs the received transactions on the manager with combined RSSI readings. This allows to execute algorithms for localization estimation.
  - Sample Logs
- LocalizationScript: Script used to estimate localization based on the monitoring logs from the manager.
- Plotters: code used to generate plots from the logs.
