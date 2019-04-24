import json
#============================ logging =========================================

# Read joson file then convert to other json file

# Read json with format:
# {"MAC": '0x0011223344556677', "JoinKey": '0x000102030405060708090A0B0C0D'}
# to ----> {"MAC": [12, 34, 56, 78, 90, 24], "JoinKey": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 33, 14, 18]}


############## Define function for converting MAC, Joinkey from HEX to DEC ###############
def convertHexStringToDec(hexStr):
    l1 =[]
    l2 =[]
    s2 ={}
    for i in range(2, len(hexStr['MAC']), 2 ):
        l1.append(int(hexStr['MAC'][i:i+2],16))
    for i in range(2, len(hexStr['JoinKey']), 2 ):
        l2.append(int(hexStr['JoinKey'][i:i+2],16))
    s2['MAC'] = l1
    s2['JoinKey'] = l2
    return s2

######## Convert MAC, Joinkey from HEX to DEC  ##############
with open('hexFile.json','r') as hexF:
    for line in hexF:
        data = json.loads(line)
        dictDec = convertHexStringToDec(data)
        print(dictDec)
        #print(data)
        with open('decFile.json','a') as decF:
            json.dump(dictDec,decF)
            decF.write('\n')