'''*********************************************************************************
SERVER - SMART PARKING LOT SYSTEM
*********************************************************************************'''
#Import the Modules Required
from pubnub import Pubnub
import json
import os
import datetime
from threading import Thread
import time
import math
import pytz
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
PARKING_LOT = "PARKING SPACE"
TIME_ZONE = ConfigSectionMap("timezone")['time_zone']

#Datablese Tables for Vehicle Info and Toll Info
DATABASE_TABLE_NAME_1 = ConfigSectionMap("table_1")['table_name']
DATABASE_TABLE_NAME_2 = ConfigSectionMap("table_2")['table_name']

# Initialize the Pubnub Keys 
PUB_KEY = ConfigSectionMap("pubnub_init")['pub_key']
SUB_KEY = ConfigSectionMap("pubnub_init")['sub_key']

# Status of the Parking lots with key words
PARKING_STATUS_FREE = 0
PARKIGN_STATUS_RESERVED = 1
PARKING_BASIC_PAY = 10

# Holds the Present Status of all the Parking Lots from the hardware 
'''{"lotNumber":"lot Status"}'''
g_orginalStatus = dict()

# Holds the Status of all Parking Lots according to the App 
'''{"lotNumber":"lot Status"}'''
g_parkingStatus = dict()		

# Notifies about Reservation Session Start and End for the individal App's
'''{"lotNumber":["sessionType","carNumber","startTime","endTime","totalTime","totalAmount"]}'''
g_sessionStatus = dict()

# Reserves the LOT and Starts the Meter
'''{"lotNumber":["carNummber","startTime","endTime"]}'''
g_smartMeter = dict()

vehicleRfid = dict()
vehicleWallet = dict()

''' Handles the Reserved Slot 
	Holds the Start Time and End Time for the lot Reserved and Closes the Reservation
	if the Car does not park and charges for the time elapsed
	{"lotNumber":["carNummber","startTime","endTime"]}
'''
g_lotReserved = dict()

# List Hold the Reserved Parking Lots and free's the list if the lot gets empty
g_lotNumberList = list()

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
	pubnub.subscribe(channels='parkingdevice-resp', callback=callback, error=callback, reconnect=reconnect, disconnect=disconnect)
	pubnub.subscribe(channels='parkingapp-req', callback=appcallback, error=appcallback, reconnect=reconnect, disconnect=disconnect)
	pubnub.subscribe(channels='parkingrfid-resp', callback=rfidCallback, error=rfidCallback, reconnect=reconnect, disconnect=disconnect)

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
		vehicleWallet.setdefault(l_temp_dict["VEHICLE_NUMBER"],l_temp_dict["WALLET_BAL"])
		try:
			l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
		except Exception as e:
			logging.error("rfid Register fetch_ERROR : " + str(e))
	ibm_db.free_stmt(l_db_statement)
	ibm_db.close(l_connection)
	print "Server Started"

'''****************************************************************************************
Function Name 		:	updateWallet
Description		:	Updates the database with Balace Amount to the Wallet
Parameters 		:	p_vehicleNum - Vehicle Numer
****************************************************************************************'''
def updateWallet(p_vehicleNum):
	l_connection = dB_init()
	if(l_connection == None):
		print("Database Connection Failed on Database Query")
		return

	update_data = "UPDATE "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1+" SET WALLET_BAL = "+str(vehicleWallet[p_vehicleNum])+" WHERE VEHICLE_NUMBER = '"+str(p_vehicleNum)+"'"

	try:
		l_db_statement = ibm_db.exec_immediate(l_connection, update_data)
		ibm_db.free_stmt(l_db_statement)
	except Exception as e:
		logging.error("Update Wallet : " + str(e))
	ibm_db.close(l_connection)

'''****************************************************************************************
Function Name 		:	updateDatabase
Description		:	Updates the database
Parameters 		:	p_vehicleNum - Vehicle Numer
					p_amount - amount to be added /deduted
					p_flag - to know add/deduct
****************************************************************************************'''
def updateDatabase(p_vehicleNum):
	l_date = datetime.datetime.now()
	l_time = l_date.strftime('%H:%M:%S')
	l_connection = dB_init()
	if(l_connection == None):
		print("Database Connection Failed on Database Query")
		return

	if(p_flag == 0):
		insert_data = "INSERT INTO "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_2+" VALUES "+"('"+str(p_vehicleNum)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_OWNER_NAME])+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_VEHICLE_TYPE]) \
			+"','"+str(PARKING_LOT)+"','"+str(l_date.date())+"','"+str(l_time)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_BALANCE])+"','"+str("0")+"','"+str("0")+"')"
	else:
		insert_data = "INSERT INTO "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_2+" VALUES "+"('"+str(p_vehicleNum)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_OWNER_NAME])+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_VEHICLE_TYPE]) \
			+"','"+str(PARKING_LOT)+"','"+str(l_date.date())+"','"+str(l_time)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_BALANCE])+"','"+str("0")+"','"+str("0")+"')"

	try:
		l_db_statement = ibm_db.exec_immediate(l_connection, insert_data)
		ibm_db.free_stmt(l_db_statement)
	
	except Exception as e:
		print e
		logging.error("dataBaseUpload_insertdata_ERROR : " + str(e))

	ibm_db.close(l_connection)

'''****************************************************************************************
Function Name 		:	databaseLogger
Description		:	Updates the database
Parameters 		:	p_rfidNumber - Respective rfid number for each vehicle
****************************************************************************************'''
def databaseLogger(p_rfidNumber):
	if vehicleRfid.has_key(p_rfidNumber):
		updateDatabase(vehicleRfid["p_rfidNumber"])

'''****************************************************************************************

Function Name 		:	checkList
Description		:	Checks the list each time the lot gets Reserved and verifies the 
					lot is not in the list
Parameters 		:	p_lotNumber - Parking lot Number 

****************************************************************************************'''
def checkList(p_lotNumber):
	l_count = 0
	for i in range(len(g_lotNumberList)):
		if (p_lotNumber == g_lotNumberList[i]):
			l_count+=1
	return l_count

'''****************************************************************************************

Function Name 		:	closeReservation
Description		:	Closes the Reservation either by timeout or the hardware deducts
					parking lot gets free
Parameters 		:	None

****************************************************************************************'''
def closeReservation():
	l_endTime = datetime.datetime.now(pytz.timezone(TIME_ZONE))
	time.sleep(1)
	print len(g_lotNumberList)
	if(len(g_lotNumberList) > 0):
		for i in range(len(g_lotNumberList)):
			if (g_orginalStatus.has_key(g_lotNumberList[i]) and g_orginalStatus[g_lotNumberList[i]] != 1 and len(g_lotNumberList) > 0):
				l_totalTime = l_endTime - g_lotReserved[g_lotNumberList[i]]
				l_totalMin = divmod(l_totalTime.days * 86400 + l_totalTime.seconds, 60)[0]
				if(l_totalMin >= 1):
					sessionEnd(g_lotNumberList[i],g_orginalStatus[g_lotNumberList[i]])
					g_parkingStatus[g_lotNumberList[i]] = g_orginalStatus[g_lotNumberList[i]]
					pubnub.publish(channel='parkingapp-resp', message={g_lotNumberList[i]:g_orginalStatus[g_lotNumberList[i]]})
					del g_lotReserved[g_lotNumberList[i]]
					del g_lotNumberList[i]
					break
			elif(g_orginalStatus.has_key(g_lotNumberList[i]) and g_orginalStatus[g_lotNumberList[i]] == 1):
				del g_lotReserved[g_lotNumberList[i]]
				del g_lotNumberList[i]
				break 
	else:
		pass

'''****************************************************************************************

Function Name 		:	sessionEnd
Description		:	Ends the Metering and Charges the User 
Parameters 		:	p_deviceid - Lot number 
					p_status - Status of the Parking Lot

****************************************************************************************'''
def sessionEnd(p_deviceid,p_status):
	if(g_smartMeter.has_key(p_deviceid) and p_status == PARKING_STATUS_FREE):
		l_endTime = datetime.datetime.now(pytz.timezone(TIME_ZONE))
		g_smartMeter[p_deviceid][2] = l_endTime
		l_etimeStr = str(l_endTime.hour) + ":" + str(l_endTime.minute) + ":" + str(l_endTime.second)
		l_parsedEndTime = datetime.datetime.strptime(l_etimeStr,'%H:%M:%S').strftime('%H:%M:%S')
		g_sessionStatus["sessionType"] = 1
		g_sessionStatus["carNum"] = g_smartMeter[p_deviceid][0]
		g_sessionStatus["lotNumber"] = p_deviceid
		g_sessionStatus["endTime"] = l_parsedEndTime
		totalTime = g_smartMeter[p_deviceid][2] - g_smartMeter[p_deviceid][1]
		l_totalMin = divmod(totalTime.days * 86400 + totalTime.seconds, 60)[0]
		l_total = math.floor(l_totalMin/60) + 1
		if l_totalMin < 1:
			g_sessionStatus["totalTime"] = "1 Minute"
		else:
			g_sessionStatus["totalTime"] = str(l_totalMin) + " Minutes"
		g_sessionStatus["totalAmt"] = (int)(l_total * PARKING_BASIC_PAY)
		if(vehicleWallet.has_key(g_smartMeter[p_deviceid][0])):
			vehicleWallet[g_smartMeter[p_deviceid][0]] = vehicleWallet[g_smartMeter[p_deviceid][0]] - g_sessionStatus["totalAmt"]
			updateWallet(g_smartMeter[p_deviceid][0])
		pubnub.publish(channel=g_smartMeter[p_deviceid][0], message=g_sessionStatus)
		del g_smartMeter[p_deviceid]
	else:
		pass

'''****************************************************************************************

Function Name 		:	carReserved
Description		:	Verifies the list did the car already parked, if not 
					Reserves the parking lot
Parameters 		:	p_lotNumber - Lot Number
					p_status - Status of the Parking Lot

****************************************************************************************'''
def carReserved(p_lotNumber,p_status):
	g_orginalStatus[p_lotNumber] = p_status
	if(checkList(p_lotNumber) != 0 and p_status == PARKING_STATUS_FREE):
		g_parkingStatus[p_lotNumber] = PARKIGN_STATUS_RESERVED
	else:
		sessionEnd(p_lotNumber,p_status)
		g_parkingStatus[p_lotNumber] = p_status
		pubnub.publish(channel='parkingapp-resp', message={p_lotNumber:p_status})

'''****************************************************************************************

Function Name 		:	appRequest
Description		:	Handles the Request sent from an app and responds with the 
					current status or with the Session start message
Parameters 		:	p_requester - Request sent from DEVICE or APP
					p_reqtype - Type of the request 
					1 : Request for the all parking lot status
					2 : Request for the Session start
					p_deviceid - Parking Lot Number
					p_carNum - Car Number

****************************************************************************************'''
def appRequest(p_requester,p_reqtype,p_deviceid,p_carNum):
	if (p_requester == "APP"):
		if (p_reqtype == 1):
			# Publishing the Status of the all the Parking Lots
			pubnub.publish(channel='parkingapp-resp', message=g_parkingStatus)
		elif (p_reqtype == 2):
			g_smartMeter[p_deviceid] = [p_carNum,0,0,0]
			if(g_smartMeter.has_key(p_deviceid)):
				l_startTime = datetime.datetime.now(pytz.timezone(TIME_ZONE))
				l_dateStr = str(l_startTime.day) + "." + str(l_startTime.month) + "." + str(l_startTime.year)
				l_stimeStr = str(l_startTime.hour) + ":" + str(l_startTime.minute) + ":" + str(l_startTime.second)
				l_parsedDate = datetime.datetime.strptime(l_dateStr,'%d.%m.%Y').strftime('%m-%d-%Y')
				l_parsedStartTime = datetime.datetime.strptime(l_stimeStr,'%H:%M:%S').strftime('%H:%M:%S')
				g_smartMeter[p_deviceid][1] = l_startTime
				g_sessionStatus["sessionType"] = 0
				g_sessionStatus["carNum"] = p_carNum
				g_sessionStatus["lotNumber"] = p_deviceid
				g_sessionStatus["parkingDate"] = l_parsedDate
				g_sessionStatus["startTime"] = l_parsedStartTime
				g_sessionStatus["endTime"] = 0
				g_sessionStatus["totalTime"] = 0
				g_sessionStatus["totalAmt"] = 0
				pubnub.publish(channel=p_carNum, message=g_sessionStatus)
				g_parkingStatus[p_deviceid] = PARKIGN_STATUS_RESERVED
				g_lotReserved[p_deviceid] = l_startTime 
				if(checkList(p_deviceid)==0):
					g_lotNumberList.append(p_deviceid)
				pubnub.publish(channel='parkingapp-resp', message=g_parkingStatus)
			else:
				pass

'''****************************************************************************************
Function Name 		:	callback
Description		:	Waits for the message from the parkingrfid-resp channel
Parameters 		:	message - RFID number from the hardware
					channel - channel for the callback
****************************************************************************************'''
def rfidCallback(message, channel):
	print message
	if(message.has_key("vehicleRFIDnum")):
		try:
			databaseLogger(message["vehicleRFIDnum"])
		except Exception as e:
			logging.error("Car Not Scanned Properly")
	else:
		pass

'''****************************************************************************************

Function Name 		:	callback
Description		:	Waits for the message from the parkingdevice-resp channel
Parameters 		:	message - Sensor Status sent from the hardware
					channel - channel for the callback
	
****************************************************************************************'''
def callback(message, channel):
	if(message.has_key("deviceID") and message.has_key("value")):
		carReserved(message["deviceID"],message["value"])
	else:
		pass

'''****************************************************************************************

Function Name 		:	appcallback
Description		:	Waits for the Request sent from the APP 
Parameters 		:	message - Request sent from the app
					channel - channel for the appcallback

****************************************************************************************'''
def appcallback(message, channel):
	if(message.has_key("requester") and message.has_key("lotNumber") and message.has_key("requestType") and message.has_key("requestValue")):
		appRequest(message["requester"],message["requestType"],message["lotNumber"],message["requestValue"])
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
	while True:
		l_timeout = Thread(target=closeReservation)
		l_timeout.start()
		l_timeout.join()

#End of the Script 
##*****************************************************************************************************##

