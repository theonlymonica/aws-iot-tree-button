#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "secrets.h"

#define BUTTON_PIN 2
#define ON_PIN 13
#define BUSY_PIN 15

int button_state = HIGH;
int last_button_state = HIGH;
unsigned long last_debounce_time = 0;
unsigned long debounce_delay = 50;
bool message_sent = false;

#define AWS_IOT_PUBLISH_TOPIC   "esp8266/pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp8266/sub"

//Timezone info
#define TZ_OFFSET +1  //Hours timezone offset to GMT (without daylight saving time)
#define TZ_DST    60  //Minutes timezone offset for Daylight saving

WiFiClientSecure net;

BearSSL::X509List cert(cacert);
BearSSL::X509List client_crt(client_cert);
BearSSL::PrivateKey key(privkey);

PubSubClient client(net);

time_t now;

void NTPConnect(void)
{
  // Set time from NTP servers
  configTime(TZ_OFFSET * 3600, TZ_DST * 60, "pool.ntp.org", "0.pool.ntp.org");
  Serial.println("\nWaiting for time");
  unsigned timeout = 5000;
  unsigned start = millis();
  while (millis() - start < timeout) {
      time_t now = time(nullptr);
      if (now > (2018 - 1970) * 365 * 24 * 3600) {
          break;
      }
      delay(100);
  }
  delay(1000); // Wait for time to fully sync
  Serial.println("Time sync'd");
  time_t now = time(nullptr);
  Serial.println(ctime(&now));
}

void messageReceived(char *topic, byte *payload, unsigned int length)
{
  Serial.print("Received [");
  Serial.print(topic);
  Serial.print("]: ");
  for (int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnectAWS()
{
  while (!client.connected())
  {
    digitalWrite(BUSY_PIN, HIGH);
    digitalWrite(ON_PIN, LOW);
    Serial.println("Attempting to reconnect to AWS IoT...");
    if (client.connect(THINGNAME))
    {
      digitalWrite(BUSY_PIN, LOW);
      digitalWrite(ON_PIN, HIGH);
      Serial.println("AWS IoT Reconnected!");
      client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC);
    }
    else
    {
      Serial.print("Failed to reconnect. Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void connectAWS()
{
  delay(1000);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.println(String("Attempting to connect to SSID: ") + String(WIFI_SSID));

  while (WiFi.status() != WL_CONNECTED)
  {
    Serial.print(".");
    delay(1000);
  }

  NTPConnect();

  net.setTrustAnchors(&cert);
  net.setClientRSACert(&client_crt, &key);

  client.setServer(MQTT_HOST, 8883);
  client.setCallback(messageReceived);

  reconnectAWS();
}

void publishMessage()
{
  StaticJsonDocument<200> doc;
  doc["message"] = "pushed";
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer); // print to client
  client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
  Serial.println("Message sent");
}

void setup()
{
  Serial.begin(115200);

  pinMode(ON_PIN, OUTPUT);
  digitalWrite(ON_PIN, LOW);
  pinMode(BUSY_PIN, OUTPUT);
  digitalWrite(BUSY_PIN, HIGH);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  connectAWS();
}

void loop() {
  if (!client.connected()) {
    reconnectAWS();
  }

  int reading = digitalRead(BUTTON_PIN);

  if (reading != last_button_state) {
    last_debounce_time = millis();
  }

  if ((millis() - last_debounce_time) > debounce_delay) {
    if (reading != button_state) {
      button_state = reading;

      if (button_state == LOW) {
        if (!message_sent) {
          Serial.println("Sending message...");
          publishMessage();
          message_sent = true;
        }
      } else {
        message_sent = false;
      }
    }
  }

  last_button_state = reading;

  client.loop();
}