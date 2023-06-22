# Arduino Code

This directory contains example Arduino codes for this IoT button project. 

## Files

The directory contains three example files:

- `https_simple.ino`: This file shows an example of invoking a Lambda function directly.
- `https_certs.ino`: This file shows an example of using an AWS IoT queue with HTTPS.
- `mqtt.ino`: This is the final code used in the project to use an AWS IoT queue with MQTT.

Please note that the first two files might require further modifications to the rest of your code and are included just for reference purposes.

## Secrets.h

Each file requires a `Secrets.h` file that should contain the necessary secrets for the AWS IoT service and your specific WiFi details. Make sure to replace the placeholder values in `Secrets.h` with your actual values before using these codes.

