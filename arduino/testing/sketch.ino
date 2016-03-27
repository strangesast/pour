#include <OneWire.h>
#include <DallasTemperature.h>

#define TEMP_PIN 2
OneWire oneWire(TEMP_PIN);
DallasTemperature sensors(&oneWire);

char tempone[15];
char temptwo[15];
char tempthr[15];

float pourFunc(float x, float w, float h, int p) {
  float y;
  y = h*(1 - pow(2, p)*pow(1/w*x - 0.5, p));
  return y;
}

String getThreeTemps() {
  //sensors.requestTemperatures();
  delay(500);
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
    Serial.println(incomingString.substring(0, 4));
    if(incomingString== "temps") {
      Serial.println("update_temps: init");
      String tempString = getThreeTemps();
      Serial.print("update_temps: ");
      Serial.println(tempString);
    } else if (incomingString== "pour") {
      float count = 0;
      float rate = 0;
      int tics = 0;
      Serial.println("pour_update: started");
      while (count < 51.00) {
        if( Serial.available() > 0 ) {
          Serial.println("pour_update: canceled");
          break;
        }
        Serial.print("pour_update: ");
        Serial.print(count);
        Serial.print(", ");
        rate = pourFunc(count, 50.0, 10.0, 6);
        Serial.print(rate);
        Serial.print(", ");
        tics += (int)rate;
        Serial.println(tics);
        count+=1.00;
        delay(1000);
      }
      Serial.println("pour_update: finished");

    } else {
      Serial.print("unrecognized, sent: ");
      Serial.println(incomingString);
    }
  }
  if( Serial && welcomed == 0 ) {
    welcomed = 1;
    Serial.println("welcome!");
  }
}
