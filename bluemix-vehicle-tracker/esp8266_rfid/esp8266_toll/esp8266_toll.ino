#include <ESP8266WiFi.h>

const char* g_ssid      = "Indiahacks";
const char* g_password  = "iamhuman";
const char* g_host      = "pubsub.pubnub.com";
const char* g_pubKey    = "pub-c-a1f796fb-1508-4c7e-9a28-9645035eee90";
const char* g_subKey    = "sub-c-d4dd77a4-1e13-11e5-9dcf-0619f8945a4f";
const char* g_channel   = "trackerrfid-resp";

/*********************************************************************************
Function Name     : setup
Description       : Initialize the Serial Communication with baud 115200, connect 
                    to the Router with SSID and PASSWORD 
Parameters        : void
Return            : void
*********************************************************************************/

void setup(void){
  Serial.begin(115200);
//  Serial.println();
//  Serial.println();
//  Serial.print("Connecting to ");
//  Serial.println(g_ssid);
  WiFi.begin(g_ssid, g_password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
//  Serial.println("");
//  Serial.println("WiFi connected");  
//  Serial.println("IP address: ");
//  Serial.println(WiFi.localIP());
  Serial.begin(9600);
}

/*********************************************************************************
Function Name     : loop
Description       : Publish the data to the hello_world channel using the 
                    GET Request 
Parameters        : void
Return            : void
*********************************************************************************/
void loop(void){
  WiFiClient client;
  const int l_httpPort = 80;
  if (!client.connect(g_host, l_httpPort)) {
    Serial.println("Pubnub Connection Failed");
    return;
  }
  String resp = "";
  char l_receivedId[13];
  char *l_vehicleId = l_receivedId;
  if(Serial.available()>0){
    for(int i =0; i<12;i++){
      l_receivedId[i] = Serial.read(); 
      delay(10);
      Serial.print(l_receivedId[i]); 
    }
    l_receivedId[12] = '\0';
  }
//DATA FORMAT : http://pubsub.pubnub.com /publish/pub-key/sub-key/signature/channel/callback/message
  if(strlen(l_vehicleId)==12){
    String l_url = "/publish/";
    l_url += g_pubKey;
    l_url += "/";
    l_url += g_subKey;
    l_url += "/0/";
    l_url += g_channel;
    l_url += "/0/";
    l_url += "{\"vehicleRFIDnum\":\"";
    l_url += l_vehicleId;
    l_url += "\"}";
    Serial.println(l_url);
    client.print(String("GET ") + l_url + " HTTP/1.1\r\n" +
               "Host: " + g_host + "\r\n" + 
               "Connection: close\r\n\r\n");
    delay(10);
  }
  memset(l_receivedId, 0, sizeof l_receivedId);  
  delay(1000);
}

//End of the Program
