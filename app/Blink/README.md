# Tag Localization with Blink
## Prerequisite
There are additional required packages which are listed in
`requirements.txt`.  Install them by the following command:

```
pip install -r requirements.txt
```

## Scripts
* manager.py: run with SmartMesh IP Manager
* tag.py: run with SmartMesh IP Mote (Slave mode)
* analyzer.py: run against a log file

## Log format

`manager.py` generates a log file each line of which is a JSON string
of an event notified by the manager.

A log line has `<notification name>` and `<notification parameter>` of
a corresponding event which are returned via `fun()` callback of
`IpMgrSubscribe.subscribe()`. In addition, `manager.py` adds the
following fields:

* `timestamp`: time when the log is recorded
* `parseed_data`: parsed data if the log is for a blink packet or health report
* `subtype`: only for a blink packet
* `macAddress` or `neighborMacAddress`: for an entry having only mote ID

MAC address is reformated by `manager.py` to a human-friendly format,
`xx-xx-xx-xx-xx-xx-xx-xx`.

Here is an example of log lines (formatted for readability):
```
{
  "timestamp": "Mon Sep 16 18:45:29 2019",
  "type": "notifData",
  "params": {"utcSecs": 1025675279, "utcUsecs": 399500, "macAddress": "00-17-0d-00-00-31-c6-a1", "srcPort": 61625, "dstPort": 61625, "data": [0, 0, 5, 0, 255, 1, 5, 0, 0, 0, 0, 61, 34, 144, 15, 0, 6, 25, 60, 0, 0, 117, 48, 1, 16, 9, 236]}
}
{
  "timestamp": "Mon Sep 16 18:45:32 2019",
  "type": "notifData",
  "parsed_data": {
    "neighbors": [
      {"macAddress": "00-17-0d-00-00-30-3e-09", "rssi": -31},
      {"macAddress": "00-17-0d-00-00-31-c1-ab", "rssi": -32},
      {"macAddress": "00-17-0d-00-00-31-c6-a1", "rssi": -43},
      {"macAddress": "00-17-0d-00-00-31-ca-03", "rssi": -44}
    ],
    "subtype": "blink",
    "user_input": "room1"
  },
  "params": {"utcSecs": 1025675280, "utcUsecs": 124500, "macAddress": "00-17-0d-00-00-38-05-e9", "srcPort": 61616, "dstPort": 61616, "data": [148, 5, 114, 111, 111, 109, 49, 149, 13, 4, 0, 1, 225, 0, 4, 224, 0, 8, 213, 0, 2, 212]}
}
{
  "timestamp": "Mon Sep 16 18:46:36 2019",
  "type": "notifHealthReport",
  "parsed_data": {
    "Device": {
      "batteryVoltage": 3243, 
      "temperature": 25,
      "numRxLost": 0,
      "numTxFail": 0,
      "numMacCrcErr": 0,
      "queueOcc": 49,
      "numNetMicErr": 0,
      "charge": 117,
      "numRxOk": 14,
      "numTxOk": 62,
      "badLinkSlot": 0,
      "numMacMicErr": 0,
      "numMacDropped": 0,
      "badLinkOffset": 0,
      "numTxBad": 0,
      "badLinkFrameId": 0
    },
    "Discovered": {
      "discoveredNeighbors": [
        {"macAddress": "00-17-0d-00-00-31-c3-19", "rssi": -16, "numRx": 3, "neighborId": 5},
        {"macAddress": "00-17-0d-00-00-31-d5-30", "rssi": -14, "numRx": 3, "neighborId": 6},
        {"macAddress": "00-17-0d-00-00-31-c6-a1", "rssi": -2, "numRx": 3, "neighborId": 8},
        {"macAddress": "00-17-0d-00-00-31-ca-03", "rssi": -16, "numRx": 2, "neighborId": 2},
        {"macAddress": "00-17-0d-00-00-31-c1-a0", "rssi": -18, "numRx": 2, "neighborId": 3},
        {"macAddress": "00-17-0d-00-00-31-c1-ab", "rssi": -9, "numRx": 2, "neighborId": 4},
        {"macAddress": "00-17-0d-00-00-31-d4-7e", "rssi": -5, "numRx": 2, "neighborId": 10}
      ],
      "numItems": 7,
      "numJoinParents": 7
    }
  },
  "params": {"macAddress": "00-17-0d-00-00-31-cc-2e", "payload": [128, 27, 0, 0, 0, 117, 49, 25, 12, 171, 0, 62, 0, 0, 0, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 130, 30, 7, 7, 0, 5, 240, 3, 0, 6, 242, 3, 0, 8, 254, 3, 0, 2, 240, 2, 0, 3, 238, 2, 0, 4, 247, 2, 0, 10, 251, 2]}
}
{
  "timestamp": "Mon Sep 16 19:02:14 2019", 
  "type": "notifHealthReport",
  "parsed_data": {
    "Neighbors": {
      "neighbors": [
        {"macAddress": "00-17-0d-00-00-31-c6-a1", "neighborFlag": 0, "neighborId": 8, "numTxFailures": 0, "rssi": -5, "numTxPackets": 91, "numRxPackets": 3},
        {"macAddress": "00-17-0d-00-00-30-3e-09", "neighborFlag": 0, "neighborId": 1, "numTxFailures": 5, "rssi": -45, "numTxPackets": 97, "numRxPackets": 3}
      ],
      "numItems": 2}
    },
  "params": {"macAddress": "00-17-0d-00-00-31-d4-7e", "payload": [129, 21, 2, 0, 8, 0, 251, 0, 91, 0, 0, 0, 3, 0, 1, 0, 211, 0, 97, 0, 5, 0, 3]}
}
```
