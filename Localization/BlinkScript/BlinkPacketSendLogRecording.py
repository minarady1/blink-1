#!/usr/bin/python

    ##
    # Send a packet into the network without joining. The mote searches for a network 
    # and sends the packet. Optionally, the list of neighbors discovered during the 
    # search process is also sent, up to a maximum of four neighbors. If the discovered 
    # neighbor list is not included, the payload maximum size is 73B, and if the discovered 
    # neighbors are included, the maximum size is 58B.
    # 
    # Upon receiving a blink command, the mote will transition to the blink state and start 
    # searching for advertisements. When it hears an advertisement, it synchronizes and continues 
    # listening briefly in efforts to discover more neighbors. After this short timeout, the 
    # mote immediately sends the data packet to one of the discovered neighbors. If the blink 
    # command is called repeatedly to send consecutive packets, the mote does not search 
    # again unless the discovered neighbor list is requested.
    # 
    # When the mote successfully sends the packet, a txDone notification will be sent with status 
    # set to 0. If the mote cannot send the packet, e.g. if 60 seconds elapse without receiving 
    # a MAC-layer acknowledgement, a txDone notification is sent with status set to 1.
    # 
    # For Blink packets, the mote can only accept a single packet at a time. To send multiple 
    # packets, the application must wait for the txDone notification. The mote will return to 
    # low-power sleep when 60 seconds elapse without any MAC-layer acknowledgements, so to 
    # prevent the mote from sleeping, the application should send the packets much faster than 
    # this 60 second timeout. See the SmartMesh Embedded IP Manager API Guide for details on 
    # the manager-side blink notification.
    # 
    # 
''' BlinkPacketSend

This scipt will connect to a mote via serial port, then issue a Blink command
It will then wait for a txDone notification signalling that the packet has left
the mote queue and is in the network. Calling this with -p X will send X packets
one after the other, waiting for txDone between each one.

Command line options include
   -c | --com to specify the COM port
   -n | --neighbors to send the packet with or without the discovered neighbors
   -p | --packets to specify how many packets to send
   -id | --experiment id of Blink mote to send blink packet 
   -h | --help 
   Example:   BlinkPacketSend.py -c COM11 -n 0 -p 2 -l Lab-room
''' 
#============================ adjust path =====================================

import sys
import os
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..','libs'))
    sys.path.insert(0, os.path.join(here, '..', '..','external_libs'))
    
#============================ imports =========================================

import threading
import traceback
import time
import json
import datetime
import random

from SmartMeshSDK                       import sdk_version
from SmartMeshSDK.IpMoteConnector       import IpMoteConnector
from SmartMeshSDK.ApiException          import APIError,                   \
                                               ConnectionError,            \
                                               QueueError

#============================ defines =========================================

UDP_PORT_NUMBER         = 60000
#STRING_TO_PUBLISH       = "Hello World!"

#============================ Functions ============================================

class NotifListener(threading.Thread):
    
    def __init__(self,connector,notifCb,disconnectedCb):
    
        # record variables
        self.connector       = connector
        self.notifCb         = notifCb
        self.disconnectedCb  = disconnectedCb
        
        # init the parent
        threading.Thread.__init__(self)
        
        # give this thread a name
        self.name            = 'NotifListener'
        
    #======================== public ==========================================
    
    def run(self):
        keepListening = True
        while keepListening:
            try:
                input = self.connector.getNotificationInternal(-1)
            except (ConnectionError,QueueError) as err:
                keepListening = False
            else:
                if input:
                    self.notifCb(input)
                else:
                    keepListening = False
        self.disconnectedCb()

def mynotifIndication(my_notif):
    # Check for txDone notification, then print status information
    if my_notif[0]==['txDone']:
        for key, value in my_notif[1].items():
            if key == "status":
                if value == 0:
                    txDoneTime = datetime.datetime.now()                    
                    jsonTime = {'TimeIssue': '{}'.format(issueTime), 'TimeTxDone': '{}'.format(txDoneTime), 'TxDone-IssueTime': '{}'.format(txDoneTime-issueTime), 'Payload':'{}'.format(STRING_TO_PUBLISH)}
                    with open('blinkMoteTime.json', 'a') as f:                    
                        f.write(json.dumps(jsonTime))
                        f.write('\n')   
                    print ('\n     txDone Status = {0}, Blink packet successfully sent\n'.format(value))                
                else:
                    print ('\n     txDone Status = {0}, Error, Blink packet NOT sent\n'.format(value))
                NotifEventDone.set()

def mydisconnectedIndication():
    print 'Mote was disconnected\n'

#============================ command line options=============================
import optparse

parser = optparse.OptionParser(usage="usage: %prog [options]")
parser.add_option("-c", "--com", dest='com', default='COM11',
                  help="COM port to connect the mote, ex: COM11")
parser.add_option("-n", "--neighbors", dest='neighbors', default=0,
                  help="Send with or without discovered neighbors, [0 | 1]")
parser.add_option("-p", "--packets", dest='packets', default=1,
                  help="Enter number of packets to send")
parser.add_option("-i", "--experiment_id", dest='experiment_id', default='A127',
                  help="Enter location of Blink mote to send packets")
(options, args) = parser.parse_args() # chu y bien options,

#============================ main ============================================

try:
    print 'BlinkPacketSend (c) Dust Networks'
    print 'SmartMesh SDK {0}\n'.format('.'.join([str(b) for b in sdk_version.VERSION]))
    print 'Note: Use with Manager Data capture utility to receive the packets\n'
    
    print 'using the following parameters: {0}\n'.format(options)
    
    #=====

    moteconnector  = IpMoteConnector.IpMoteConnector()
    moteconnector.connect({'port': options.com})

    # start a NotifListener
    NotifEventDone = threading.Event()
    mynotifListener   = NotifListener (
                          moteconnector,
                          mynotifIndication,
                          mydisconnectedIndication,
                          )
    mynotifListener.start()

    #=====
    print "\n- sending {0} Blink packet(s) with discovered neighbors set to {1}\n".format(int(options.packets),int(options.neighbors))

    for i in range(0, int(options.packets)):
        try:
            timePoch = time.time()
            #STRING_TO_PUBLISH       = "{}__".format(options.location)+ "{}{}{}{}__{}".format(random.randint(1000000000, 9999999999),random.randint(1000000000, 9999999999), random.randint(1000000000, 9999999999), random.randint(1000000000, 9999999999), i+1)
            #STRING_TO_PUBLISH       = "{}__".format(options.location) + "{}__{}".format(timePoch, i+1)
            STRING_TO_PUBLISH       = "{}_".format(options.experiment_id) + "{}_{}".format(i+1, timePoch)
            resp = moteconnector.dn_blink(
                fIncludeDscvNbrs    = int(options.neighbors),
                payload             = [ord(i) for i in STRING_TO_PUBLISH],
            )            
            print '    Requested a Blink with payload --> "{0}"'.format(STRING_TO_PUBLISH)
            # Wtire capture time in json file here
            issueTime = datetime.datetime.now()
        except Exception as err:
            print ("Could not execute dn_blink: {0}\n".format(err))
               
        print "...waiting for packet sent Notifaction",       
        while not NotifEventDone.is_set():
            print '!',
            time.sleep(1)

        NotifEventDone.clear()
    moteconnector.disconnect()
  
    print 'Script ended normally.'

except Exception as err:
    output  = []
    output += ["Script ended with an error!"]
    output += [""]
    output += ["======== exception ==========="]
    output += [""]
    output += [str(err)]
    output += [""]
    output += ["======== trace ==============="]
    output += [""]
    output += [traceback.format_exc()]
    output += ["=============================="]
    output += [""]
    output  = '\n'.join(output)
    print output
    
    tout = 30
    while tout:
        print 'closing in {0} s...'.format(tout)
        time.sleep(1)
        tout -= 1
    sys.exit()
