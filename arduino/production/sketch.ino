#include <OneWire.h>
#include <DallasTemperature.h>

#define TEMP_PIN 2
#define RELAY_PIN 5
#define INTERRUPT_PIN 1 // corresponds to pin 3

OneWire oneWire(TEMP_PIN);
DallasTemperature sensors(&oneWire);

volatile int counter = 0;  // flow counter

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

void blink() {
    counter++;
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  attachInterrupt(INTERRUPT_PIN, blink, RISING);
  sensors.begin();
  getThreeTemps();
  Serial.begin(9600);
}

String incomingString = "nothing yet";
int welcomed = 0;

unsigned long pourTimeoutMillis = 50000;
unsigned long pourMaxMillis = 50000;
unsigned long pourStartMillis = 0;
unsigned long pourCurrentMillis = 0;
boolean pourCanceled = false;

void loop() {
  if( Serial.available() > 0 ) {
    incomingString = Serial.readStringUntil('\n');
    counter = 0;

    if(incomingString == "temps") {
      Serial.print("fetching temps...\n");
      String tempString = getThreeTemps();
      Serial.print("update-temps: ");
      Serial.println(tempString);
    } else if (incomingString == "pour") {
      digitalWrite(RELAY_PIN, HIGH);  // open valve
      pourStartMillis = millis();
      pourCurrentMillis = pourStartMillis + 1;
      pourCanceled = false;

      while(pourCurrentMillis - pourStartMillis < pourMaxMillis) {
        pourCurrentMillis = millis();
        if(Serial.available() > 0) {
          incomingString = Serial.readStringUntil('\n');
          pourCanceled = true;
          Serial.println("pour_update: canceled");
        }

        if(pourCurrentMillis > pourTimeoutMillis && counter < 25) {
          pourCanceled = true;
          Serial.println("pour_update: timeout");
        }

        Serial.print("pour_update: ");
        Serial.print(pourCurrentMillis);
        Serial.print(", ");
        Serial.println(counter);

        if(pourCanceled) {
          break;
        }
      }
      Serial.flush();
      digitalWrite(RELAY_PIN, LOW);  // close valve
      Serial.println("pour_update: finished");

    } else {
      Serial.print("invalid_send: ");
      Serial.println(incomingString);
    }
  }
  if( Serial && welcomed == 0 ) {
    welcomed = 1;
    Serial.println("welcome!");
  }
}
