# bluemix-transportation-infrastructure

Time and efficiency are a matter of priority in present days. Our main objective is to build a system for NH toll plaza that reduces the traffic at peak hours using our Smart Toll Plaza System with RFID as an enhancement to the currently deployed manual toll collection system.

We built a RFID based smart toll collection system makes toll transaction more convenient for travellers. Considering the present toll collection system , where all vehicles have to stop and pay taxes. On an average each vehicle passing through a toll plaza has to wait approx. 2 minute in a toll at engine start condition which thereby aids in air pollution and wastage of fuel & money. If this system comes to existence, the waiting time at toll plaza will be reduced.This system has a unique feature whereby the system can report a stolen vehicle if the vehicle’s owner blocks it.

Now, The server is running on the local computer. In future, the same can be hosted to the online servers and system can be installed at many NH TOLLS, also as a enhancement for tracking the accident vehicle details and used for the automated parking lots tracking the vehicle number.

## Video And Presentation

PRESENTATION
https://he-s3.s3.amazon.../2a86a01description.pdf

DEMO
https://youtu.be/f_9NVZJMjYg

## INSTRUCTIONS TO RUN

# SERVER REQUIREMENTS:

iNSTALLING THE PUBNUB TO RUN SERVER PROGRAM

               pip install pubnub>=3.7.5
To run the server follow the command in terminal:

             - cd automated-toll-collection-system/toll-server/
             - python server.py
## DEVICE BUILD

Step 1: Setting up the IDE to Program the ESP8266

# Installing the Arduino ESP8266 Core with the Boards Manager

-   Download and Install Arduino 1.6.6 from [https://www.arduino.cc/en/Main/Software]
-   Start Arduino and open Preferences window.
-   Enter http://arduino.esp8266.com/stable/package_esp8266com_index.json into Additional Board Manager URLs field. 
-   You can add multiple URLs, separating them with commas.
-   Open Boards Manager from Tools > Boards > Board menu and install esp8266 platform (and don't forget to select your ESP8266 board from Tools > Board menu after installation).

# Uploading the Program to the ESP8266 using the Arduino IDE

Step 1: Get this Git Repo to your desktop using,

        git clone https://github.com/suryasundarraj/automated-toll-collection-system.git
Step 2: Open the codes in Arduino IDE

Step 3: Select the NodeMCU 1.0(ESP8266 V12-E), 80Mhz,115200

Step 4: Select the USB Port from Tools - > Port

Step 5: Edit the SSID and PASSWORD to configure to your router

Step 6: Edit the pubnub publish and subscribe keys to your unique key provided by pubnub.com(if required)

Step 7: Upload the Code to the ESP8266

(Note: Connect the GPIO 0 to GND to Pull the ESP8266 to Flashing Mode)

## MOBILE APP BUILD

Steps to be followed to Build and Run the Android App for Automated System (Note : Assumed Cordova framework installed in your system) (For pre-compiled app follow Step 4) Step 1 : Change the cordova project directory

        cd (folder_name)
Step 2 : Modify the pubnub publish and subscribe keys at www/js/index.js

Step 3 : Build the .apk file using,

        cordova build android
Step 4 : Once the .apk file is build successfully, you will find the app at this path

        ./platforms/android/build/output/android-debug.apk
Step 5 : Install the APP on an Android Phone.
