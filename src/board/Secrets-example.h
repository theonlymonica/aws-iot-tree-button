#include <pgmspace.h>

#define SECRET

const char WIFI_SSID[] = "XXXXXXXXXXXX";
const char WIFI_PASSWORD[] = "YYYYYYYYYYYYYY";

#define THINGNAME "button"

const char MQTT_HOST[] = "abcdefghijkl-ats.iot.eu-west-1.amazonaws.com";

// Amazon Root CA 1
static const char cacert[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
)EOF";

// Device Certificate
static const char client_cert[] PROGMEM = R"KEY(
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
)KEY";

// Device Private Key
static const char privkey[] PROGMEM = R"KEY(
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
)KEY";