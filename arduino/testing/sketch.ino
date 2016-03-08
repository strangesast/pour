#include <OneWire.h>
#include <DallasTemperature.h>

#define TEMP_PIN 2
OneWire oneWire(TEMP_PIN);
DallasTemperature sensors(&oneWire);

char tempone[15];
char temptwo[15];
char tempthr[15];

String getThreeTemps() {
  //sensors.requestTemperatures();
  delay(1000);
  dtostrf(18.1114, 4, 4, tempone);
  dtostrf(19.2831, 4, 4, temptwo);
  dtostrf(20.0012, 4, 4, tempthr);
  return String() + tempone + ", " + temptwo + ", " + tempthr;
}

void setup() {
  Serial.begin(9600);
  //sensors.begin();
  getThreeTemps();
}

String incomingString = "nothing yet";
int welcomed = 0;

void loop() {
  Serial.flush();
  if( Serial.available() > 0 ) {
    incomingString = Serial.readStringUntil('\n');
    if(incomingString == "temps") {
      Serial.print("fetching temps...\n");
      String tempString = getThreeTemps();
      Serial.print("update-temps: ");
      Serial.println(tempString);
    } else if (incomingString == "pour") {
      int count = 0;
      while (count < 10) {
        Serial.println(count);
        count++;
        delay(1000);
      }
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
