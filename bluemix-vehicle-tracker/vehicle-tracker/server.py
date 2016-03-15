'''*********************************************************************************
SERVER - VEHICLE TRACKER
*********************************************************************************'''
#Import the Modules Required
from pubnub import Pubnub
import os
import datetime
import logging
import ConfigParser

# Modules for the dashDB
import ibm_db
from ibm_db import connect, active

#Importing the Config File and Parsing the file using the ConfigParser
config_file = "./config.ini"
Config = ConfigParser.ConfigParser()
Config.read(config_file)
logging.basicConfig(filename='logger.log',level=logging.DEBUG)

'''****************************************************************************************
Function Name 		:	ConfigSectionMap
Description		:	Parsing the Config File and Extracting the data and returning it
Parameters 		:	section - section to be parserd
****************************************************************************************'''
def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            logging.debug("exception on %s!" % option)
            dict1[option] = None
    return dict1

#Database Related Variables and Lists 
DB_SCHEMA = ConfigSectionMap("database")['db_schema'] 
DB_HOST = ConfigSectionMap("database")['db_host']
DB_NAME = ConfigSectionMap("database")['db_name']
DB_USER_NAME = ConfigSectionMap("database")['username']
DB_PASSWORD = ConfigSectionMap("database")['pwd']
DB_PORT = ConfigSectionMap("database")['port']

#Datablese Tables for Vehicle Info and Toll Info
DATABASE_TABLE_NAME_1 = ConfigSectionMap("table_1")['table_name']
DATABASE_TABLE_NAME_2 = ConfigSectionMap("table_2")['table_name']

# Initialize the Pubnub Keys 
PUB_KEY = ConfigSectionMap("pubnub_init")['pub_key']
SUB_KEY = ConfigSectionMap("pubnub_init")['sub_key']

#Data Structures
vehicleRfid = dict()

vehicleDetails = dict()
DETAILS_USER_NAME = 0
DETAILS_CONTACT_NUMBER = 1
DETAILS_EM_NUMBER_1 = 2
DETAILS_EM_NUMBER_2 = 3
DETAILS_ADDRESS		= 4

'''****************************************************************************************

Function Name 		:	init
Description		:	Initalize the pubnub keys and Starts Subscribing from the 
					parkingdevice-resp and parkingapp-req channels
Parameters 		:	None

****************************************************************************************'''
def init():
	#Pubnub Initialization
	global pubnub 
	pubnub = Pubnub(publish_key=PUB_KEY,subscribe_key=SUB_KEY)
	pubnub.subscribe(channels='trackerapp-req', callback=appcallback, error=appcallback, reconnect=reconnect, disconnect=disconnect)
	pubnub.subscribe(channels='trackerrfid-resp', callback=rfidCallback, error=rfidCallback, reconnect=reconnect, disconnect=disconnect)

'''****************************************************************************************
Function Name 		:	dB_init
Description		:	Initalize the Database and establishing the connection between the 
					database and the kitchen-tracker
Parameters 		:	None
****************************************************************************************'''
def dB_init():
	dbtry = 0
	while (dbtry < 3):
		try:
			if 'VCAP_SERVICES' in os.environ:
			    hasVcap = True
			    import json
			    vcap_services = json.loads(os.environ['VCAP_SERVICES'])
			    if 'dashDB' in vcap_services:
			        hasdashDB = True
			        service = vcap_services['dashDB'][0]
			        credentials = service["credentials"]
			        url = 'DATABASE=%s;uid=%s;pwd=%s;hostname=%s;port=%s;' % ( credentials["db"],credentials["username"],credentials["password"],credentials["host"],credentials["port"])
			    	print "VCAP",url    
			    else:
			        hasdashDB = False
			else:
			    hasVcap = False
			    url = 'DATABASE=%s;uid=%s;pwd=%s;hostname=%s;port=%s;' % (DB_NAME,DB_USER_NAME,DB_PASSWORD,DB_HOST,DB_PORT)
			connection = ibm_db.connect(url, '', '')
			if (active(connection)):
				return connection
		except Exception as error:
			logging.debug("dataBase connection_ERROR : " + str(error))
			dbtry+=1
	return None

'''****************************************************************************************
Function Name 		:	defaultLoader_settings
Description		:	If RFID Number is not registered with server, here it registers it
Parameters 		:	None
****************************************************************************************'''
def defaultLoader_settings():
	l_connection = dB_init()
	if(l_connection == None):
		print("Database Connection Failed on Database Query")
		return
	l_database_query = "SELECT * FROM "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1
	try:
		l_db_statement = ibm_db.exec_immediate(l_connection, l_database_query)
		l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
	except Exception as e:
		logging.error("rfid Register exec/fetch_ERROR : " + str(e))
	
	while l_temp_dict:
		vehicleRfid.setdefault(l_temp_dict["RFID"],l_temp_dict["VEHICLE_NUMBER"])
		vehicleDetails.setdefault(l_temp_dict["VEHICLE_NUMBER"],[l_temp_dict["USER_NAME"],l_temp_dict["CONTACT_NUMBER"],l_temp_dict["EMERGENCY_NUMBER_1"],l_temp_dict["EMERGENCY_NUMBER_2"],l_temp_dict["ADDRESS"]])
		try:
			l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
		except Exception as e:
			logging.error("rfid Register fetch_ERROR : " + str(e))
	ibm_db.free_stmt(l_db_statement)
	ibm_db.close(l_connection)
	print "Server Started"

'''****************************************************************************************
Function Name 		: 	trackerUpdate
Description		:	If RFID Number is registered with server, here it responds with the 
					information
Parameters 		:	None
****************************************************************************************'''
def trackerUpdate(p_rfidNumber):
	message = {}
	if(vehicleRfid.has_key(p_rfidNumber)):
		try:
			message["ownerName"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_USER_NAME]
			message["contactNum"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_CONTACT_NUMBER]
			message["emergencyNum1"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_EM_NUMBER_1]
			message["emergencyNum2"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_EM_NUMBER_2]
			message["address"]	=	vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_ADDRESS]
			pubnub.publish(channel="trackerapp-resp",message=message)
			message.clear()
		except Exception as e:
			print e

'''****************************************************************************************
Function Name 		:	rfidCallback
Description		:	Waits for the message from the parkingrfid-resp channel
Parameters 		:	message - RFID number from the hardware
					channel - channel for the callback
****************************************************************************************'''
def rfidCallback(message, channel):
	if(message.has_key("vehicleRFIDnum")):
		try:
			trackerUpdate(message["vehicleRFIDnum"])
		except Exception as e:
			print e
			logging.error("Car Not Scanned Properly")
	else:
		pass

'''****************************************************************************************

Function Name 		:	appcallback
Description		:	Waits for the Request sent from the APP 
Parameters 		:	message - Request sent from the app
					channel - channel for the appcallback

****************************************************************************************'''
def appcallback(message, channel):
	if(message.has_key("requester") and message.has_key("requestType")):
		pass
		# appRequest(message["requester"],message["requestType"],message["userId"])
	else:
		pass

'''****************************************************************************************

Function Name 		:	error
Description		:	If error in the channel, prints the error
Parameters 		:	message - error message

****************************************************************************************'''
def error(message):
    print("ERROR : " + str(message))

'''****************************************************************************************

Function Name 		:	reconnect
Description		:	Responds if server connects with pubnub
Parameters 		:	message

****************************************************************************************'''
def reconnect(message):
    print("RECONNECTED")

'''****************************************************************************************

Function Name 		:	disconnect
Description		:	Responds if server disconnects from pubnub
Parameters 		:	message

****************************************************************************************'''
def disconnect(message):
    print("DISCONNECTED")

'''****************************************************************************************

Function Name 		:	__main__
Description		:	Conditional Stanza where the Script starts to run
Parameters 		:	None

****************************************************************************************'''
if __name__ == '__main__':
	#Initialize the Script
	init()
	defaultLoader_settings()

#End of the Script 
##*****************************************************************************************************##

