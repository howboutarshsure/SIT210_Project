#include <ArduinoBLE.h>

// Pin definitions for motor control
const int enA = 9;    // PWM pin to control motor speed
const int in1 = 8;    // IN1 pin of L298N
const int in2 = 7;    // IN2 pin of L298N

// BLE service and characteristic UUIDs
const char* SERVICE_UUID = "180F";
BLEUnsignedCharCharacteristic garageCharacteristic("2A19", BLERead | BLENotify | BLEWrite); // BLE Characteristic

// Initialize BLE service and characteristic
BLEService garageService(SERVICE_UUID);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Set all the motor control pins to output
  pinMode(enA, OUTPUT);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);

  // Initial motor state: stop
  stopMotor();

  // Initialize BLE
  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }

  // Set the local name and advertise the service
  BLE.setLocalName("GarageDoor");
  BLE.setAdvertisedService(garageService);

  // Add the characteristic to the service
  garageService.addCharacteristic(garageCharacteristic);
  BLE.addService(garageService);

  garageCharacteristic.writeValue(0);
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
      if (garageCharacteristic.written()) {
        unsigned char commandChar = garageCharacteristic.value();
        String command = String((char)commandChar);

        Serial.print("Received command: ");
        Serial.println(command);

        if (command == "o") {
          moveMotorClockwise(255);  // Open the garage door
        } else if (command == "c") {
          moveMotorCounterclockwise(255);  // Close the garage door
        } else if (command == "f") {
          stopMotor();  // Turn off the motor
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
  digitalWrite(in1, HIGH);
  digitalWrite(in2, LOW);

  // Set motor speed
  analogWrite(enA, speed);
}

void moveMotorCounterclockwise(int speed) {
  Serial.println("Motor moving counterclockwise");
  // Set motor direction to counterclockwise
  digitalWrite(in1, LOW);
  digitalWrite(in2, HIGH);

  // Set motor speed
  analogWrite(enA, speed);
}

void stopMotor() {
  Serial.println("Motor stopped");
  // Set both IN1 and IN2 to LOW to stop the motor
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);

  // Turn off the motor by setting the speed to 0
  analogWrite(enA, 0);
}