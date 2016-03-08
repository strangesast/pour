#include <OneWire.h>
#include <DallasTemperature.h>

#define TEMP_PIN 2
OneWire oneWire(TEMP_PIN);
DallasTemperature sensors(&oneWire);

char tempone[15];
char temptwo[15];
char tempthr[15];

String getThreeTemps() {
  sensors.requestTemperatures();
  dtostrf(sensors.getTempCByIndex(0), 4, 4, tempone);
  dtostrf(sensors.getTempCByIndex(1), 4, 4, temptwo);
  dtostrf(sensors.getTempCByIndex(2), 4, 4, tempthr);
  return String() + tempone + ", " + temptwo + ", " + tempthr;
}

void setup() {
  Serial.begin(9600);
  sensors.begin();
  getThreeTemps();
}

String incomingString = "nothing yet";
int welcomed = 0;

void loop() {
  if( Serial.available() > 0 ) {
    incomingString = Serial.readStringUntil('\n');
    if(incomingString == "temps") {
      Serial.print("fetching temps...\n");
      String tempString = getThreeTemps();
      Serial.print("update-temps: ");
      Serial.println(tempString);
    } else {
      Serial.print("sent: ");
      Serial.println(incomingString);
    }
  }
  if( Serial && welcomed == 0 ) {
    welcomed = 1;
    Serial.println("welcome!");
  }
}
