#include <ArduinoBLE.h>

// Pin definitions for motor control
const int enB = 9;    // PWM pin to control motor speed
const int in3 = 8;    // IN3 pin of L298N
const int in4 = 7;    // IN4 pin of L298N

// BLE service and characteristic UUIDs
const char* FAN_SERVICE_UUID = "1810"; // Unique UUID for the fan service
const char* FAN_CHARACTERISTIC_UUID = "2A1A"; // Unique UUID for the fan characteristic
BLEUnsignedCharCharacteristic fanCharacteristic(FAN_CHARACTERISTIC_UUID, BLERead | BLENotify | BLEWrite); // BLE Characteristic

// Initialize BLE service and characteristic
BLEService fanService(FAN_SERVICE_UUID);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Set all the motor control pins to output
  pinMode(enB, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);

  // Initial motor state: stop
  stopMotor();

  // Initialize BLE
  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }

  // Set the local name and advertise the service
  BLE.setLocalName("Fan");
  BLE.setAdvertisedService(fanService);

  // Add the characteristic to the service
  fanService.addCharacteristic(fanCharacteristic);
  BLE.addService(fanService);

  fanCharacteristic.writeValue(0);
  // Start advertising
  BLE.advertise();
  
  Serial.println("BLE device is now advertising...");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    while (central.connected()) {
      if (fanCharacteristic.written()) {
        unsigned char commandChar = fanCharacteristic.value();
        String command = String((char)commandChar);

        Serial.print("Received command: ");
        Serial.println(command);

        if (command == "o") {
          moveMotorClockwise(255);  // Turn on the fan
        } else if (command == "f") {
          stopMotor();  // Turn off the fan
        } else {
          Serial.println("Unknown command");
        }
      }
    }
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());

    // Start advertising again
    BLE.advertise();
    Serial.println("BLE device is now advertising...");
  }
}

void moveMotorClockwise(int speed) {
  Serial.println("Motor moving clockwise");
  // Set motor direction to clockwise
  digitalWrite(in3, HIGH);
  digitalWrite(in4, LOW);

  // Set motor speed
  analogWrite(enB, speed);
}

void stopMotor() {
  Serial.println("Motor stopped");
  // Set both IN3 and IN4 to LOW to stop the motor
  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);

  // Turn off the motor by setting the speed to 0
  analogWrite(enB, 0);
}
