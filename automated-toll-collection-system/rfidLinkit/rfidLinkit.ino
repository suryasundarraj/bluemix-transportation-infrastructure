#include <LWiFi.h>
#include <LWiFiClient.h>
#include "SPI.h"
#include "./PubNub.h"
#include "settings.h"

#define channel "vehicleIdentificanDevice-resp"
char g_jsonResponse[26];

void setup() {
  Serial.begin(9600);
  Serial1.begin(9600);
  //Connecting to the local AP using the SSID and Password
  while (0 == LWiFi.connect(WIFI_AP, LWiFiLoginInfo(WIFI_AUTH, WIFI_PASSWORD)))
  {
      Serial.println(" . ");
      delay(1000);
  }
  //Initialize PubNub PUB SUB keys
  PubNub.begin(pubkey, subkey);
}

/*******************************************************************************************************
 Function Name            : prepare_json_data
 Description              : Prepares the json data to be published to the pubnub channel
 Parameters               : p_containerId,p_weight
          p_containerId   : The Unique ID for the container
          p_weight        : Present weight in the specfic container
 *******************************************************************************************************/
void prepare_json_data(const char* p_rfidNum)
{
  strcat(g_jsonResponse,"{\"vehicleRFIDnum\":\"");
  strcat(g_jsonResponse,p_rfidNum);
  strcat(g_jsonResponse,"\"}");
}

void loop() {
  char l_receivedId[13];
  char *l_vehicleId = l_receivedId;
  if(Serial1.available()>0){
    for(int i =0; i<12;i++){
      l_receivedId[i] = Serial1.read(); 
      delay(10);
      Serial.print(l_receivedId[i]); 
    }
    l_receivedId[12] = '\0';
    prepare_json_data(l_vehicleId);
    Serial.println(g_jsonResponse);
    pubnubPublish(g_jsonResponse);
    memset(g_jsonResponse, 0, sizeof(g_jsonResponse)); 
  }
}

/*******************************************************************************************************
 Function Name            : pubnubPublish
 Description              : Publish the data to the specfied channel 
 Parameters               : p_data
                p_data    : data to be published in the given channel
 *******************************************************************************************************/
void pubnubPublish(char *p_data){
  LWiFiClient *client;
  client = PubNub.publish(channel,p_data);
  if (!client) {
      Serial.println("publishing error");
      delay(1000);
      return;
  }
  while (client->connected()) {
      while (client->connected() && !client->available()); // wait
      char c = client->read();
      Serial.print(c);
  }
  client->stop();
}
//End of the Program
/*******************************************************************************************************************************/
