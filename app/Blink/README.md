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
    "timestamp": "Tue Sep 17 14:24:14 2019",
    "type": "notifData",
    "params": {"utcSecs": 1025666368, "utcUsecs": 11250, "macAddress": "00-17-0d-00-00-31-c3-71", "srcPort": 61625, "dstPort": 61625, "data": [0, 0, 5, 0, 255, 1, 5, 0, 0, 0, 0, 61, 34, 109, 64, 0, 0, 59, 240, 0, 0, 117, 48, 1, 16, 9, 34]}
}

{
    "timestamp": "Tue Sep 17 14:24:25 2019",
    "type": "notifData",
    "parsed_data": {
        "neighbors": [
            {"macAddress": "00-17-0d-00-00-30-3e-09", "location": "A124", "rssi": -36},
            {"macAddress": "00-17-0d-00-00-31-d5-20", "location": "A124", "rssi": -46},
            {"macAddress": "00-17-0d-00-00-31-d4-7e", "location": "A123", "rssi": -54},
            {"macAddress": "00-17-0d-00-00-31-c3-37", "location": "A126", "rssi": -61}
        ],
        "subtype": "blink", "user_input": "A124"
    },
    "params": {"utcSecs": 1025666376, "utcUsecs": 689500, "macAddress": "00-17-0d-00-00-38-05-e9", "srcPort": 61616, "dstPort": 61616, "data": [148, 4, 65, 49, 50, 52, 149, 13, 4, 0, 1, 220, 0, 8, 210, 0, 7, 202, 0, 13, 195]}
}

{
    "timestamp": "Tue Sep 17 14:29:33 2019",
    "type": "notifHealthReport",
    "parsed_data": {
        "Device": {
            "batteryVoltage": 3319,
            "temperature": 23,
            "numRxLost": 0,
            "numTxFail": 0,
            "numMacCrcErr": 24,
            "queueOcc": 49,
            "numNetMicErr": 0,
            "charge": 226,
            "numRxOk": 11,
            "numTxOk": 59,
            "badLinkSlot": 0,
            "numMacMicErr": 0,
            "numMacDropped": 0,
            "badLinkOffset": 0,
            "numTxBad": 0,
            "badLinkFrameId": 0
        },
        "Discovered": {
            "discoveredNeighbors": [
                {"macAddress": "00-17-0d-00-00-31-c1-a0", "rssi": -64, "numRx": 18, "neighborId": 16},
                {"macAddress": "00-17-0d-00-00-31-c6-b8", "rssi": -42, "numRx": 2, "neighborId": 2},
                {"macAddress": "00-17-0d-00-00-31-d5-86", "rssi": -52, "numRx": 2, "neighborId": 3},
                {"macAddress": "00-17-0d-00-00-31-d5-3b", "rssi": -43, "numRx": 2, "neighborId": 4},
                {"macAddress": "00-17-0d-00-00-31-cc-40", "rssi": -49, "numRx": 2, "neighborId": 5},
                {"macAddress": "00-17-0d-00-00-31-d5-20", "rssi": -50, "numRx": 2, "neighborId": 8},
                {"macAddress": "00-17-0d-00-00-31-cb-e7", "rssi": -68, "numRx": 2, "neighborId": 9},
                {"macAddress": "00-17-0d-00-00-31-d1-a8", "rssi": -59, "numRx": 2, "neighborId": 10}
            ],
            "numItems": 8,
            "numJoinParents": 8
        }
    },
    "params": {"macAddress": "00-17-0d-00-00-31-d4-7e", "payload": [128, 27, 0, 0, 0, 226, 49, 23, 12, 247, 0, 59, 0, 0, 0, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 24, 130, 34, 8, 8, 0, 16, 192, 18, 0, 2, 214, 2, 0, 3, 204, 2, 0, 4, 213, 2, 0, 5, 207, 2, 0, 8, 206, 2, 0, 9, 188, 2, 0, 10, 197, 2]}
}
```
