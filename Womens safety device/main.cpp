#include <Wire.h>
#include <Adafruit_ADXL345_U.h>
#include <MAX30100_PulseOximeter.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// === I2C Setup ===
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);
PulseOximeter pox;

// === Serial Pins ===
// GPS (D7=RX, D8=TX)
SoftwareSerial gpsSerial(D7, D8);

// GSM (D5=RX, D6=TX)
SoftwareSerial gsmSerial(D5, D6);
TinyGPSPlus gps;

// === Target Phone Number ===
String phoneNumber = "+919363236208";

// === Timer ===
#define REPORT_INTERVAL_MS 60000  // 1 minute
uint32_t lastSMSSent = 0;

// === Function Prototypes ===
void sendGSMCommand(String cmd, int wait = 1000);
void sendSMS(String number, String text);

void setup() {
  Serial.begin(9600);
  Wire.begin(D2, D1); // SDA, SCL

  // Accelerometer init
  if (!accel.begin()) {
    Serial.println("ADXL345 not detected");
    while (1);
  }

  // Heart rate sensor init
  if (!pox.begin()) {
    Serial.println("MAX30100 failed to start");
  }
  pox.setIRLedCurrent(MAX30100_LED_CURR_7_6MA);

  gpsSerial.begin(9600);
  gsmSerial.begin(9600);
  delay(1000);

  // Init GSM
  sendGSMCommand("AT");
  sendGSMCommand("AT+CMGF=1");  // SMS text mode
  Serial.println("Setup complete.");
}

void loop() {
  sensors_event_t event;
  accel.getEvent(&event);

  pox.update();
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  if (millis() - lastSMSSent >= REPORT_INTERVAL_MS && gps.location.isValid()) {
    lastSMSSent = millis();

    float ax = event.acceleration.x;
    float ay = event.acceleration.y;
    float az = event.acceleration.z;
    float hr = pox.getHeartRate();
    float spo2 = pox.getSpO2();
    double lat = gps.location.lat();
    double lon = gps.location.lng();

    String message = "Accel: X=" + String(ax, 2) + " Y=" + String(ay, 2) + " Z=" + String(az, 2);
    message += "\nHR: " + String(hr, 1) + "bpm, SpO2: " + String(spo2, 1) + "%";
    message += "\nGPS: " + String(lat, 6) + "," + String(lon, 6);
    message+="\n\n\nEmergency";
    message+="\nTrack the location";

    sendSMS(phoneNumber, message);
  }

  if (gsmSerial.available()) {
    Serial.write(gsmSerial.read());
  }
}

void sendGSMCommand(String cmd, int wait) {
  gsmSerial.println(cmd);
  delay(wait);
  while (gsmSerial.available()) {
    Serial.write(gsmSerial.read());
  }
}

void sendSMS(String number, String text) {
  gsmSerial.print("AT+CMGS=\"");
  gsmSerial.print(number);
  gsmSerial.println("\"");
  delay(500);
  gsmSerial.print(text);
  delay(500);
  gsmSerial.write(26); // CTRL+Z
  Serial.println("SMS Sent!");
}