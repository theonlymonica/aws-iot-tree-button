#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>

#define STASSID "iPhone XS"
#define STAPSK "provaprova"

#define BUTTON_PIN 2
#define ON_PIN 13
#define BUSY_PIN 15

const char* ssid = STASSID;
const char* password = STAPSK;

String url = "https://srhwu5yyfz3ma72nn5ij77f5am0cavnd.lambda-url.eu-south-1.on.aws";
String body = "username=admin&password=cun3pnwZAT4dmg1zbu";

int last_pin_state = LOW;
int pin_state;
unsigned long last_time =  0;
unsigned long delay_time = 200;

void setup() {
  Serial.begin(115200);

  pinMode(ON_PIN, OUTPUT);
  digitalWrite(ON_PIN, LOW);
  pinMode(BUSY_PIN, OUTPUT);
  digitalWrite(BUSY_PIN, LOW);

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  digitalWrite(ON_PIN, HIGH);
}

void loop() {

  pin_state = digitalRead(BUTTON_PIN);

  if (pin_state != last_pin_state) {
    last_time = millis();
  }

  if ( (millis() - last_time) > delay_time) {
    digitalWrite(BUSY_PIN, HIGH);

    if (pin_state == LOW) {
      last_pin_state = 0;
      if ((WiFi.status() == WL_CONNECTED)) {

          std::unique_ptr<BearSSL::WiFiClientSecure>client(new BearSSL::WiFiClientSecure);
          client->setInsecure();
          HTTPClient https;

          Serial.print("[HTTPS] START\n");
          https.begin(*client, url);

          https.addHeader("User-Agent", "ESP8266");

          Serial.print("[HTTPS] POST...\n");
          int httpsCode = https.POST(body);

          if (httpsCode > 0) {
            Serial.println(httpsCode);
            if (httpsCode == HTTP_CODE_OK) {
              Serial.println(https.getString());
            }
          } else {
              Serial.println("failed to POST");
          }
          Serial.print("[HTTPS] END\n");
          https.end();
          digitalWrite(BUSY_PIN, LOW);
        }
    } else {
        last_pin_state = 1;
    }
  }
}