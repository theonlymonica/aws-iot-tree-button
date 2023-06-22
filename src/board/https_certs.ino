#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

// AWS IoT topic
const char* AWS_IOT_TOPIC = "esp8266/pub";

// Button pin
const int BUTTON_PIN = 2;

// Debounce variables
int button_state = HIGH;
int last_button_state = HIGH;
unsigned long last_debounce_time = 0;
unsigned long debounce_delay = 200;

// Message sent flag
bool message_sent = false;

BearSSL::X509List cert(cacert);
BearSSL::X509List client_crt(client_cert);
BearSSL::PrivateKey key(privkey);

// NTP time synchronization
void setupNTP() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("Waiting for NTP time sync");
  while (!time(nullptr)) {
    delay(100);
  }
  Serial.println("NTP synchronized");
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  setupNTP();

  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  // Read the button state
  int reading = digitalRead(BUTTON_PIN);

  // Perform button debouncing
  if (reading != last_button_state) {
    last_debounce_time = millis();
  }

  if ((millis() - last_debounce_time) > debounce_delay) {
    if (reading != button_state) {
      button_state = reading;

      if (button_state == LOW) {
        if (!message_sent) {
          // Button pressed, send HTTPS request
          Serial.println("Sending HTTPS POST request...");

          BearSSL::WiFiClientSecure client;
          client.setClientRSACert(&client_crt, &key);
          client.setTrustAnchors(&cert);

          HTTPClient http;
          http.begin(client, "https://" + String(AWS_IOT_ENDPOINT) + ":" + String(AWS_IOT_PORT) + "/topics/" + String(AWS_IOT_TOPIC) + "?qos=1");
          http.addHeader("Content-Type", "text/plain");

          StaticJsonDocument<200> doc;
          doc["message"] = "pushed";
          char jsonBuffer[512];
          serializeJson(doc, jsonBuffer);

          int httpResponseCode = http.POST(jsonBuffer);
          if (httpResponseCode == HTTP_CODE_OK) {
            Serial.println(http.getString());
          } else {
            Serial.print("HTTP POST request failed with error code: ");
            Serial.println(httpResponseCode);
            Serial.println(http.getString());
          }

          http.end();

          message_sent = true;
        }
      } else {
        message_sent = false;
      }
    }
  }

  // Update the button state
  last_button_state = reading;
}
