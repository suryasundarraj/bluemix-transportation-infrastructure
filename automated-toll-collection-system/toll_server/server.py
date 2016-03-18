'''*********************************************************************************
SERVER - AUTOMATED TOLL BOOTH
*********************************************************************************'''
#Import the Modules Required
import os
from pubnub import Pubnub
import datetime
import ConfigParser
import logging
import time

# Modules for the dashDB
import ibm_db
from ibm_db import connect, active

#DATA STRUCTURES
vehicleDetails = dict()
DETAILS_BALANCE = 0
DETAILS_OWNER_NAME = 1
DETAILS_VEHICLE_TYPE = 2
DETAILS_BLOCK_STATUS = 3

vehicleRfid = dict()

vehicleSetting = dict()

vehicleTransaction = dict()

transVehicle = dict()

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

#CONSTANTS
TOLL_CHARGE = 50
TOLL_CROSSED = "NH14 TOLL"
BASIC_AMOUNT = 500

# Initialize the Pubnub Keys 
PUB_KEY = ConfigSectionMap("pubnub_init")['pub_key']
SUB_KEY = ConfigSectionMap("pubnub_init")['sub_key']

'''****************************************************************************************
Function Name 		:	init
Description		:	Initalize the pubnub keys and Starts Subscribing 
Parameters 		:	None
****************************************************************************************'''
def init():
	#Pubnub Initialization
	global pubnub 
	pubnub = Pubnub(publish_key=PUB_KEY,subscribe_key=SUB_KEY)
	pubnub.subscribe(channels='vehicleIdentificanDevice-resp', callback=callback, error=callback, reconnect=reconnect, disconnect=disconnect)
	pubnub.subscribe(channels='vehicleIdentificanApp-req', callback=appcallback, error=appcallback, reconnect=reconnect, disconnect=disconnect)


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
Function Name 		:	defaultLoader
Description		:	If RFID Number is not registered with server, here it registers it
Parameters 		:	p_rfidNumber - RFID Unique Number
****************************************************************************************'''
def defaultLoader(p_rfidNumber):
	if(not vehicleRfid.has_key(p_rfidNumber)):
		l_connection = dB_init()
		if(l_connection == None):
			print("Database Connection Failed on Database Query")
			return
		l_database_query = "SELECT * FROM "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1+" WHERE RFID = '"+str(p_rfidNumber)+"'"
		try:
			l_db_statement = ibm_db.exec_immediate(l_connection, l_database_query)
			l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
		except Exception as e:
			logging.error("rfid Register exec/fetch_ERROR : " + str(e))
		
		while l_temp_dict:
			if(l_temp_dict["RFID"] == p_rfidNumber):
				vehicleRfid.setdefault(p_rfidNumber,l_temp_dict["VEHICLE_NUMBER"])
				vehicleDetails.setdefault(vehicleRfid[p_rfidNumber],[l_temp_dict["WALLET_BAL"],l_temp_dict["USER_NAME"],l_temp_dict["VEHICLE_TYPE"],l_temp_dict["BLOCK_STATUS"]])
			try:
				l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
			except Exception as e:
				logging.error("rfid Register fetch_ERROR : " + str(e))
		ibm_db.free_stmt(l_db_statement)
		ibm_db.close(l_connection)

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
		vehicleDetails.setdefault(vehicleRfid[l_temp_dict["RFID"]],[l_temp_dict["WALLET_BAL"],l_temp_dict["USER_NAME"],l_temp_dict["VEHICLE_TYPE"],l_temp_dict["BLOCK_STATUS"]])
		try:
			l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
		except Exception as e:
			logging.error("rfid Register fetch_ERROR : " + str(e))
	ibm_db.free_stmt(l_db_statement)
	ibm_db.close(l_connection)
	print "Server Started"

'''****************************************************************************************
Function Name 		:	updateBlockStatus
Description		:	If vehicle is blocked,updates to the database
Parameters 		:	p_vehicleNum - Vehicle Numer
					p_blockStatus - Block Status of the respective vehicle
****************************************************************************************'''	
def updateBlockStatus(p_vehicleNum,p_blockStatus):
	l_connection = dB_init()
	if(l_connection == None):
		print("Database Connection Failed on Database Query")
		return

	update_data = "UPDATE "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1+" SET BLOCK_STATUS = "+str(p_blockStatus)+" WHERE VEHICLE_NUMBER = '"+str(p_vehicleNum)+"'"

	try:
		l_db_statement = ibm_db.exec_immediate(l_connection, update_data)
		ibm_db.free_stmt(l_db_statement)
	except Exception as e:
		logging.error("Update Wallet : " + str(e))
	ibm_db.close(l_connection)

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

	update_data = "UPDATE "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1+" SET WALLET_BAL = "+str(vehicleDetails[p_vehicleNum][DETAILS_BALANCE])+" WHERE VEHICLE_NUMBER = '"+str(p_vehicleNum)+"'"

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
def updateDatabase(p_vehicleNum,p_amount,p_flag):
	l_date = datetime.datetime.now()
	l_time = l_date.strftime('%H:%M:%S')
	l_connection = dB_init()
	if(l_connection == None):
		print("Database Connection Failed on Database Query")
		return

	if(p_flag == 0):
		insert_data = "INSERT INTO "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_2+" VALUES "+"('"+str(p_vehicleNum)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_OWNER_NAME])+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_VEHICLE_TYPE]) \
			+"','"+str(TOLL_CROSSED)+"','"+str(l_date.date())+"','"+str(l_time)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_BALANCE])+"','"+str("0")+"','"+str(p_amount)+"')"
	else:
		insert_data = "INSERT INTO "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_2+" VALUES "+"('"+str(p_vehicleNum)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_OWNER_NAME])+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_VEHICLE_TYPE]) \
			+"','"+str(TOLL_CROSSED)+"','"+str(l_date.date())+"','"+str(l_time)+"','"+str(vehicleDetails[p_vehicleNum][DETAILS_BALANCE])+"','"+str(p_amount)+"','"+str("0")+"')"

	try:
		l_db_statement = ibm_db.exec_immediate(l_connection, insert_data)
		ibm_db.free_stmt(l_db_statement)
	
	except Exception as e:
		logging.error("dataBaseUpload_insertdata_ERROR : " + str(e))

	ibm_db.close(l_connection)
	updateWallet(p_vehicleNum)

'''****************************************************************************************
Function Name 		:	appSetting
Description		:	Once App request for the settings, server responds with the details
					and block status
Parameters 		:	p_vehicleNumber - Vehicle Number 
					p_blockStatus - Responds with block status is active
****************************************************************************************'''
def appSetting(p_vehicleNumber,p_blockStatus):
	if(p_vehicleNumber != None and p_blockStatus != None):
		if(vehicleDetails.has_key(p_vehicleNumber)):
			vehicleSetting["vehicleNumber"] = p_vehicleNumber
			vehicleSetting["availableBal"] = vehicleDetails[p_vehicleNumber][DETAILS_BALANCE]
			vehicleSetting["ownerName"] = vehicleDetails[p_vehicleNumber][DETAILS_OWNER_NAME]
			vehicleSetting["vehicleType"] = vehicleDetails[p_vehicleNumber][DETAILS_VEHICLE_TYPE]
			vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS] = int(p_blockStatus)
			vehicleSetting["blockStatus"] = vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS]
			if(vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS] == 0):
				pubnub.publish(channel=p_vehicleNumber, message=vehicleSetting)
				updateBlockStatus(p_vehicleNumber,vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS])
				appTransaction(p_vehicleNumber)				
			else:
				updateBlockStatus(p_vehicleNumber,vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS])
				pubnub.publish(channel=p_vehicleNumber, message={"warning":"Vehicle is Blocked"})
		else:
			pubnub.publish(channel=p_vehicleNumber, message={"warning":"Vehicle Not Registered with the Automated System"})
	else:
		pass


'''****************************************************************************************
Function Name 		:	generalSetting
Description		:	Once App request for the settings, server responds with the details
Parameters 		:	p_vehicleNumber - Vehicle Number 
****************************************************************************************'''
def generalSetting(p_vehicleNumber):
	if(p_vehicleNumber != None):
		if(vehicleDetails.has_key(p_vehicleNumber)):
			if(vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS] == 0):
				pubnub.publish(channel=p_vehicleNumber, message={"vehicleNumber":p_vehicleNumber,"availableBal":vehicleDetails[p_vehicleNumber][DETAILS_BALANCE],"ownerName":vehicleDetails[p_vehicleNumber][DETAILS_OWNER_NAME],\
					"vehicleType":vehicleDetails[p_vehicleNumber][DETAILS_VEHICLE_TYPE]})
				l_connection = dB_init()
				if(l_connection == None):
					print("Database Connection Failed on Database Query")
					return
				l_database_query = "SELECT * FROM "+DB_SCHEMA+"."+DATABASE_TABLE_NAME_1+" WHERE VEHICLE_NUMBER = '"+str(p_vehicleNumber)+"'"
				try:
					l_db_statement = ibm_db.exec_immediate(l_connection, l_database_query)
					l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
				except Exception as e:
					logging.error("rfid Register exec/fetch_ERROR : " + str(e))
				
				while l_temp_dict:
					if(l_temp_dict["VEHICLE_NUMBER"] == p_vehicleNumber):
						vehicleDetails[p_vehicleNumber][DETAILS_BALANCE] = l_temp_dict["WALLET_BAL"]
					try:
						l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
					except Exception as e:
						logging.error("rfid Register fetch_ERROR : " + str(e))
				ibm_db.free_stmt(l_db_statement)
				ibm_db.close(l_connection)
				pubnub.publish(channel=p_vehicleNumber, message={"vehicleNumber":p_vehicleNumber,"availableBal":vehicleDetails[p_vehicleNumber][DETAILS_BALANCE],"ownerName":vehicleDetails[p_vehicleNumber][DETAILS_OWNER_NAME],\
					"vehicleType":vehicleDetails[p_vehicleNumber][DETAILS_VEHICLE_TYPE]})
			else:
				appSetting(p_vehicleNumber,vehicleDetails[p_vehicleNumber][DETAILS_BLOCK_STATUS])
		else:
			pubnub.publish(channel=p_vehicleNumber, message={"warning":"Vehicle Not Registered with the Automated System"})
	else:
		pass

'''****************************************************************************************
Function Name 		:	vehicleIdentified
Description		:	When the vehicle is scanned, the amount is deducted
Parameters 		:	p_rfidNumber - Unique RFID Number
****************************************************************************************'''
def vehicleIdentified(p_rfidNumber):
	if(vehicleRfid.has_key(p_rfidNumber)):
		message = {}
		l_todayDate = datetime.datetime.now()
		l_date1 = l_todayDate.strftime('%d-%m-%Y %H:%M:%S')
		l_date = l_todayDate.strftime('%d-%m-%Y')
		l_time = l_todayDate.strftime('%H:%M:%S')
		if(vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_BLOCK_STATUS] == 0):
			if(vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_BALANCE] < 0):
				message["warning"] = "Please Recharge"
			else:
				message["warning"] = " "
				vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_BALANCE] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_BALANCE] - TOLL_CHARGE
			message["vehicleNumber"] = vehicleRfid[p_rfidNumber]
			message["availableBal"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_BALANCE]
			message["ownerName"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_OWNER_NAME]
			message["vehicleType"] = vehicleDetails[vehicleRfid[p_rfidNumber]][DETAILS_VEHICLE_TYPE]
			message["amtDeducted"] = TOLL_CHARGE
			message["NHCrossed"] = TOLL_CROSSED
			message["dateTime"] = l_date
			message["dateTime1"] = l_time
			pubnub.publish(channel=vehicleRfid[p_rfidNumber], message=message)
			updateDatabase(vehicleRfid[p_rfidNumber],TOLL_CHARGE,0)
			appTransaction(vehicleRfid[p_rfidNumber])
		else:
			message["NHCrossed"] = TOLL_CROSSED	
			message["dateTime"] = l_date
			message["dateTime1"] = l_time
			message["warning"] = "Vehicle is Blocked"
			pubnub.publish(channel=vehicleRfid[p_rfidNumber], message=message)
	else:
		pass

'''****************************************************************************************
Function Name 		:	appRecharge
Description		:	Rechares the amount for each user
Parameters 		:	p_vehicleNum - Vehicle Number
					p_rechargeAmt - Required Recharge Amount
****************************************************************************************'''
def appRecharge(p_vehicleNum,p_rechargeAmt):
	if(vehicleDetails.has_key(p_vehicleNum)):
		vehicleDetails[p_vehicleNum][DETAILS_BALANCE] = vehicleDetails[p_vehicleNum][DETAILS_BALANCE] + int(p_rechargeAmt)
		vehicleSetting["vehicleNumber"] = p_vehicleNum
		vehicleSetting["availableBal"] = vehicleDetails[p_vehicleNum][DETAILS_BALANCE]
		vehicleSetting["ownerName"] = vehicleDetails[p_vehicleNum][DETAILS_OWNER_NAME]
		vehicleSetting["vehicleType"] = vehicleDetails[p_vehicleNum][DETAILS_VEHICLE_TYPE]
		pubnub.publish(channel=p_vehicleNum, message=vehicleSetting)
		l_todayDate = datetime.datetime.now()
		l_date = l_todayDate.strftime('%d-%m-%Y %H:%M:%S')
		updateDatabase(p_vehicleNum,p_rechargeAmt,1)
		appTransaction(p_vehicleNum)
	else:
		pass

'''****************************************************************************************
Function Name 		:	appTransaction
Description		:	When app requests for the Transaction details, responds the details
					of the previous transaction
Parameters 		:	p_vehicleNum - Vehicle Number
****************************************************************************************'''
def appTransaction(p_vehicleNum):
	if(vehicleDetails.has_key(p_vehicleNum)):
		l_connection = dB_init()
		if(l_connection == None):
			print("Database Connection Failed on Database Query")
			return
		dateorder_query = "SELECT * FROM DASH6461.TOLL_DATA WHERE VEHICLE_NUMBER = \'"+str(p_vehicleNum)+"\' ORDER BY DATES DESC,TIME DESC LIMIT 5"
		try:
			l_db_statement = ibm_db.exec_immediate(l_connection, dateorder_query)
			l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
		except Exception as e:
			logging.error("appHistoricalGraph_twodatequery exec/fetch_ERROR : " + str(e))
		l_count = 0
		while l_temp_dict:
			l_new_date = l_temp_dict["DATES"].strftime("%d-%m-%Y")
			l_new_time = l_temp_dict["TIME"].strftime("%H:%M:%S")
			l_final_date = l_new_date + " " + l_new_time
			vehicleTransaction[l_count] = [l_final_date,l_temp_dict["TOLL_NAME"],l_temp_dict["AMOUNT_DEDUCT"],l_temp_dict["AMOUNT_ADDED"],l_temp_dict["AVAI_BAL"]]
			l_count+=1			
			try:
				l_temp_dict = ibm_db.fetch_assoc(l_db_statement)
			except Exception as e:
				logging.error("appHistoricalGraph_twodatequery fetch_ERROR : " + str(e))
		transVehicle[p_vehicleNum] = vehicleTransaction
		ibm_db.free_stmt(l_db_statement)
		ibm_db.close(l_connection)
		pubnub.publish(channel=p_vehicleNum+p_vehicleNum,message=transVehicle[p_vehicleNum])
	else:
		pass

'''****************************************************************************************
Function Name 		:	callback
Description		:	Waits for the message from the vehicleIdentificanDevice-resp channel
Parameters 		:	message - Sensor Status sent from the hardware
					channel - channel for the callback
****************************************************************************************'''
def callback(message, channel):
	if(message.has_key("vehicleRFIDnum")):
		try:
			defaultLoader(message["vehicleRFIDnum"])
			vehicleIdentified(message["vehicleRFIDnum"])
		except Exception as e:
			logging.error("Car ID Not Scanned Properly")
	else:
		pass

'''****************************************************************************************
Function Name 		:	appcallback
Description		:	Waits for the Request sent from the APP 
Parameters 		:	message - Request sent from the app
					channel - channel for the appcallback
****************************************************************************************'''
def appcallback(message, channel):
	# 0 - Update Status, 1 - Rechare Amt, 2 - Transaction History
	if(message.has_key("requester") and message.has_key("requestType")):
		if(message["requestType"] == 0 and message.has_key("vehicleNumber")):
			if(message.has_key("requestValue")):
				appSetting(message["vehicleNumber"],message["requestValue"])
			else:
				generalSetting(message["vehicleNumber"])
		elif(message["requestType"] == 1 and message.has_key("vehicleNumber")):
			appRecharge(message["vehicleNumber"],message["rechargeAmt"])
		elif(message["requestType"] == 2 and message.has_key("vehicleNumber")):
			if(transVehicle.has_key(message["vehicleNumber"])):
				pubnub.publish(channel=message["vehicleNumber"]+message["vehicleNumber"],message=transVehicle[message["vehicleNumber"]])
		else:
			pass
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

 
