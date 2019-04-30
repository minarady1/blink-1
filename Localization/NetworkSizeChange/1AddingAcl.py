#!/usr/bin/python

#============================ adjust path =====================================

import sys
import os
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..','libs'))
    sys.path.insert(0, os.path.join(here, '..', '..','external_libs'))

#============================ verify installation =============================

from SmartMeshSDK.utils import SmsdkInstallVerifier
(goodToGo,reason) = SmsdkInstallVerifier.verifyComponents(
    [
        SmsdkInstallVerifier.PYTHON,
        SmsdkInstallVerifier.PYSERIAL,
    ]
)
if not goodToGo:
    print "Your installation does not allow this application to run:\n"
    print reason
    raw_input("Press any button to exit")
    sys.exit(1)

#============================ imports =========================================

import random
import traceback
from SmartMeshSDK                       import sdk_version
from SmartMeshSDK.IpMgrConnectorSerial  import IpMgrConnectorSerial
from SmartMeshSDK.IpMoteConnector       import IpMoteConnector
from SmartMeshSDK.utils                 import AppUtils, \
                                               FormatUtils
import json
#============================ logging =========================================

# local
import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('App')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

# global
AppUtils.configureLogging()

#============================ defines =========================================

DEFAULT_MGRSERIALPORT   = 'COM15'
DEFAULT_MOTESERIALPORT  = 'COM19'

#============================ helper functions ================================

#============================ main ============================================

try:
    # Connect to Manager
    manager        = IpMgrConnectorSerial.IpMgrConnectorSerial()
    print 'ACL creation (c) Dust Networks'
    print 'SmartMesh SDK {0}\n'.format('.'.join([str(b) for b in sdk_version.VERSION]))
    
    print '==== Connect to manager'
    serialport     = raw_input("Serial port of SmartMesh IP Manager (e.g. {0}): ".format(DEFAULT_MGRSERIALPORT))
    serialport     = serialport.strip()
    if not serialport:
        serialport = DEFAULT_MGRSERIALPORT
    manager.connect({'port': serialport})
    print 'Connected to manager at {0}.\n'.format(serialport)
 
    # Create ACL until the final of file
            
    print '    Create ACL on the manager...\n',
    
    with open('decFile.json','r') as MacFile:
        for line in MacFile:
            data = json.loads(line)
            print('MAC address {}'.format(FormatUtils.formatBuffer(data['MAC'])))
            #print(data['MAC'])
            manager.dn_setACLEntry(
                macAddress   = data['MAC'],
                joinKey      = data['JoinKey'],
            )
            if not line:
                f.close()
    print 'done.'

    

    print '\n\n==== disconnect from manager'
    manager.disconnect()
    print 'Bye bye.\n'
    
except Exception as err:
    output  = []
    output += ['=============']
    output += ['CRASH']
    output += [str(err)]
    output += [traceback.format_exc()]
    print '\n'.join(output)
else:
    print 'Script ended normally'
finally:
    raw_input("Press Enter to close.")
