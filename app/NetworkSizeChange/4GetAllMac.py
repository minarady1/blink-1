#!/usr/bin/python

'''
Available commands:
 - help (h): print this menu
 - info (i): information about this application
 - quit (q): quit this application
 - uptime (ut): how long this application has been running
 - connect (c): connect to a serial port
 - allMotes (a): list all motes accessed into network
 - operMotes (o): list all current operational motes of network
 - notifs (n): toggle whether to print OAP notifications

'''

#============================ adjust path =====================================

import sys
import os
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..','libs'))
    sys.path.insert(0, os.path.join(here, '..', '..','external_libs'))

#============================ imports =========================================

# built-in
import time
import threading
import traceback
import json
import datetime

# SmartMeshSDK
from SmartMeshSDK                                 import sdk_version
from SmartMeshSDK.utils                           import FormatUtils
from SmartMeshSDK.IpMgrConnectorSerial            import IpMgrConnectorSerial
from SmartMeshSDK.IpMgrConnectorMux               import IpMgrSubscribe
from SmartMeshSDK.ApiException                    import APIError, \
                                                         ConnectionError,  \
                                                         CommandTimeoutError
from SmartMeshSDK.protocols.oap                   import OAPDispatcher, \
                                                         OAPClient,     \
                                                         OAPMessage,    \
                                                         OAPNotif

# DustCli
from dustCli      import DustCli

#============================ defines =========================================

NUM_BCAST_TO_SEND  = 2

#============================ globals =========================================

#============================ helpers =========================================

def printExcAndQuit(err):
    output  = []
    output += ["="*30]
    output += ["error"]
    output += [str(err)]
    output += ["="*30]
    output += ["traceback"]
    output += [traceback.format_exc()]
    output += ["="*30]
    output += ["Script ended because of an error. Press Enter to exit."]
    output  = '\n'.join(output)
    
    raw_input(output)
    sys.exit(1)

def getAllMotes():

    operationalmotes = [] 
    # get list of operational motes
    currentMac     = (0,0,0,0,0,0,0,0) # start getMoteConfig() iteration with the 0 MAC address
    continueAsking = True
    while continueAsking:
        try:
            res = AppData().get('connector').dn_getMoteConfig(currentMac,True)
        except APIError:
            continueAsking = False
        else:
            if ((not res.isAP) and (res.state in [0,1,4])):
                operationalmotes += [tuple(res.macAddress)]
            currentMac = res.macAddress
    AppData().set('operationalmotes',operationalmotes)
    
    # create an oap_client for each operational mote
    oap_clients = AppData().get('oap_clients')
    for mac in operationalmotes:
        if mac not in oap_clients:
            oap_clients[mac] = OAPClient.OAPClient(
                mac,
                AppData().get('connector').dn_sendData,
                AppData().get('oap_dispatch'),
            )
    
    return len(operationalmotes)
def getOperationalMotes():

    operationalmotes = [] 
    # get list of operational motes
    currentMac     = (0,0,0,0,0,0,0,0) # start getMoteConfig() iteration with the 0 MAC address
    continueAsking = True
    while continueAsking:
        try:
            res = AppData().get('connector').dn_getMoteConfig(currentMac,True)
        except APIError:
            continueAsking = False
        else:
            if ((not res.isAP) and (res.state in [4,])):
                operationalmotes += [tuple(res.macAddress)]
            currentMac = res.macAddress
    AppData().set('operationalmotes',operationalmotes)
    
    # create an oap_client for each operational mote
    oap_clients = AppData().get('oap_clients')
    for mac in operationalmotes:
        if mac not in oap_clients:
            oap_clients[mac] = OAPClient.OAPClient(
                mac,
                AppData().get('connector').dn_sendData,
                AppData().get('oap_dispatch'),
            )
    
    return len(operationalmotes)
    
def printAllMotes():
    strMac ={}
    strTime={}
    output  = []
    output += ["Ther are total {0} motes accessed into network:".format(len(AppData().get('operationalmotes')))]
    strTime['currentTime'] = '{}'.format(datetime.datetime.now())
    print(strTime)
    with open('AllMotes.json','a') as operF:
        json.dump(strTime, operF)
        operF.write('\n')
    for (i,m) in enumerate(AppData().get('operationalmotes')):
        output += ['MoteID {0}: {1}'.format(i+2,FormatUtils.formatMacString(m))]
        strMac['MACHex'] = FormatUtils.formatMacString(m)
        strMac['MoteID'] = i+2
        with open('AllMotes.json','a') as operF:
            json.dump(strMac, operF)
            operF.write('\n')
    output  = '\n'.join(output)    
    print output

def printOperationalMotes():
    strMac ={}
    strTime={}
    output  = []
    output += ["Currently, there are {0} operational motes in network:".format(len(AppData().get('operationalmotes')))]
    strTime['currentTime'] = '{}'.format(datetime.datetime.now())
    print(strTime)
    with open('OperationalMotes.json','a') as operF:
        json.dump(strTime, operF)
        operF.write('\n')
    for (i,m) in enumerate(AppData().get('operationalmotes')):
        output += ['MAC Address: {}'.format(FormatUtils.formatMacString(m))]
        strMac['MACHex'] = FormatUtils.formatMacString(m)
        #strMac['Mote Oder'] = i
        with open('OperationalMotes.json','a') as operF:
            json.dump(strMac, operF)
            operF.write('\n')
    output  = '\n'.join(output)    
    print output

def togglePrintNotifs():
    
    if AppData().get('printNotifs')==False:
        AppData().set('printNotifs',True)
        print "notifications are ON."
    else:
        AppData().set('printNotifs',False)
        print "notifications are OFF."


#============================ classes =========================================

class AppData(object):
    #======================== singleton pattern ===============================
    _instance = None
    _init     = False
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppData, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    def __init__(self):
        # singleton
        if self._init:
            return
        self._init = True
        # variables
        self.dataLock   = threading.RLock()
        self.data       = {}
    #======================== public ==========================================
    def set(self,k,v):
        with self.dataLock:
            self.data[k] = v
    def get(self,k):
        with self.dataLock:
            return self.data[k]
    def delete(self,k):
        with self.dataLock:
            del self.data[k]

class Manager(object):
    
    def __init__(self):
        
        
        # OAP dispatcher
        AppData().set('oap_dispatch',OAPDispatcher.OAPDispatcher())
        AppData().get('oap_dispatch').register_notif_handler(self._handle_oap_notif)
        
        # subscriber
        self.subscriber = IpMgrSubscribe.IpMgrSubscribe(AppData().get('connector'))
        self.subscriber.start()
        self.subscriber.subscribe(
            notifTypes =    [
                                IpMgrSubscribe.IpMgrSubscribe.NOTIFDATA,
                            ],
            fun =           self._cb_NOTIFDATA,
            isRlbl =        False,
        )
        
        # list operational motes
        AppData().set('oap_clients',{})          
        AppData().set('printNotifs',False)
        togglePrintNotifs()

        # Added to calculate Mgr vs system time offset in the log prints
        self.mapmgrtime = MgrTime(0, 20)
        self.mapmgrtime.start()
        
    #======================== public ==========================================
    
    def disconnect(self):
        AppData().get('connector').disconnect()
    
    #======================== private =========================================
    
    def _cb_NOTIFDATA(self,notifName,notifParams):
        
        AppData().get('oap_dispatch').dispatch_pkt(notifName, notifParams)
        if AppData().get('logNotifs'):
            if notifParams.data[0] == 0:
                self.log_file.write (' Pkt queued Time  ---> {0}.{1:0>6}\n'.format(notifParams.utcSecs, notifParams.utcUsecs))

    def _handle_oap_notif(self,mac,notif):

        receive_time = float(time.time()) - self.mapmgrtime.pctomgr_time_offset
        output  = "OAP notification from {0} (receive time {1}):\n{2}".format(
            FormatUtils.formatMacString(mac),
            receive_time,
            notif
        )
        
        if AppData().get('printNotifs'):
            print output
        if AppData().get('logNotifs'):
            self.log_file.write('{0}\n'.format(output))

class MgrTime(threading.Thread):
    '''
    This class periodically sends a getTime() API command to the manager to map
    network time to UTC time. The offset is used to calculate the pkt arrival
    time for the same time base as the mote.
    '''

    def __init__(self, pctomgr_time_offset, sleepperiod):
        # init the parent
        threading.Thread.__init__(self)
        self.event                  = threading.Event()
        self.sleepperiod            = sleepperiod
        self.daemon                 = True
        self.pctomgr_time_offset    = pctomgr_time_offset
        # give this thread a name
        self.name                   = 'MgrTime'               

    def run(self):
        while True:
            # Get PC time and send the getTime command to the Manager
            pc_time = float(time.time())
            mgr_timepinres = AppData().get('connector').dn_getTime()
            mgr_time = mgr_timepinres.utcSecs + mgr_timepinres.utcUsecs / 1000000.0
            mgr_asn = int(''.join(["%02x"%i for i in mgr_timepinres.asn]),16)
            self.pctomgr_time_offset = pc_time - mgr_time
            
            self.event.wait(self.sleepperiod)

#============================ CLI handlers ====================================

def connect_clicb(params):
    
    # filter params
    port = params[0]
    
    try:
        AppData().get('connector')
    except KeyError:
        pass
    else:
        print 'already connected.'
        return
    
    # create a connector
    AppData().set('connector',IpMgrConnectorSerial.IpMgrConnectorSerial())
    
    # connect to the manager
    try:
        AppData().get('connector').connect({
            'port': port,
        })
    except ConnectionError as err:
        print 'Could not connect to {0}: {1}'.format(
            port,
            err,
        )
        AppData().delete('connector')
        return
    
    # start threads
    AppData().set('manager',Manager())

def list_clicb(params):
    getAllMotes()
    printAllMotes()

def list_oper_clicb(params):
    getOperationalMotes()
    printOperationalMotes()

def notifs_clicb(params):
    togglePrintNotifs()

def quit_clicb():
    
    if AppData().get('connector'):
        AppData().get('connector').disconnect()
    if AppData().get('manager'):
        AppData().get('manager').disconnect()
    
    time.sleep(.3)
    print "bye bye."

#============================ main ============================================

def main():
    
    # create CLI interface
    cli = DustCli.DustCli(
        quit_cb  = quit_clicb,
        versions = {
            'SmartMesh SDK': sdk_version.VERSION,
        },
    )
    cli.registerCommand(
        name                      = 'connect',
        alias                     = 'c',
        description               = 'connect to a serial port',
        params                    = ['portname'],
        callback                  = connect_clicb,
        dontCheckParamsLength     = False,
    )
    cli.registerCommand(
        name                      = 'allMotes',
        alias                     = 'a',
        description               = 'list all motes accessed into network',
        params                    = [],
        callback                  = list_clicb,
        dontCheckParamsLength     = False,
    )
    cli.registerCommand(
        name                      = 'operMotes',
        alias                     = 'o',
        description               = 'list all current operational motes of network',
        params                    = [],
        callback                  = list_oper_clicb,
        dontCheckParamsLength     = False,
    )
    
    cli.registerCommand(
        name                      = 'notifs',
        alias                     = 'n',
        description               = 'toggle whether to print OAP notifications',
        params                    = [],
        callback                  = notifs_clicb,
        dontCheckParamsLength     = False,
    )


if __name__=='__main__':
    main()
