import firebase_admin
from firebase_admin import credentials, db
from bluepy import btle
import time
import threading
import smbus2
import os
import json

# Initialize Firebase
cred = credentials.Certificate("/home/arshsure/temp/garagedoor-68d7b-firebase-adminsdk-p1sqi-2eb27c543b.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://garagedoor-68d7b-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# Reference to the Firebase database paths
db_ref_garage = db.reference('garage')
db_ref_fan = db.reference('fan')

# Bluetooth MAC addresses
GARAGE_MAC = "EC:62:60:81:4C:0A"
FAN_MAC = "D4:D4:DA:4E:F5:DA"  # Replace with actual MAC address

# UUIDs for Garage Door
GARAGE_SERVICE_UUID = "180F"
GARAGE_CHARACTERISTIC_UUID = "2A19"

# UUIDs for Fan
FAN_SERVICE_UUID = "1810"
FAN_CHARACTERISTIC_UUID = "2A1A"

class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

def send_data_to_device(device, data):
    if data == "off":
        data = "f"
    if device == "garage":
        mac_address = GARAGE_MAC
        service_uuid = GARAGE_SERVICE_UUID
        characteristic_uuid = GARAGE_CHARACTERISTIC_UUID
    else:
        mac_address = FAN_MAC
        service_uuid = FAN_SERVICE_UUID
        characteristic_uuid = FAN_CHARACTERISTIC_UUID
    
    try:
        # Connect to the device
        peripheral = btle.Peripheral(mac_address)
        peripheral.setDelegate(MyDelegate())
        
        # Enable notifications
        svc = peripheral.getServiceByUUID(service_uuid)
        char = svc.getCharacteristics(characteristic_uuid)[0]
        
        char.write(data.encode('utf-8'), withResponse=True)
        print(f"Sent data to {device}: {data}")
        
        peripheral.disconnect()
        print(f"Disconnected from {device}")
        

        
        return True
    except btle.BTLEException as e:
        print(f"Failed to send data to {device}: {e}")
        return False

def save_command_locally(device, command):
    filename = f'latest_command_{device}.json'
    
    valid_commands = {
        "garage": ["open", "close", "off"],
        "fan": ["on", "off"]
    }
    
    # Initialize all commands to False
    commands = {cmd: False for cmd in valid_commands.get(device, [])}
    
    # Set the given command to True
    commands[command] = True
    
    # Save the updated commands to the file
    with open(filename, 'w') as file:
        json.dump(commands, file)

def load_latest_command(device):
    filename = f'latest_command_{device}.json'
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return None

def check_wifi():
    response = os.system("ping -c 1 google.com > /dev/null 2>&1")
    return response == 0

def sync_with_firebase():
    if check_wifi():
        for device in ["garage", "fan"]:
            latest_command = load_latest_command(device)
            if latest_command:
                db_ref = db.reference(device)
                try:
                    db_ref.update(latest_command)
                    os.remove(f'latest_command_{device}.json')
                except Exception as e:
                    print(f"Failed to update Firebase for {device}: {e}")

# Function to listen for Firebase database changes
def firebase_listener(event, device):
    data = event.data
    print(f"Received {device} status: {data}")
    
    if data:
        for command, status in data.items():
            if status:
                if send_data_to_device(device, command):
                    display_to_lcd(f"{device.capitalize()}", f"{command.capitalize()}")

def terminal_listener():
    while True:
        user_input = input("Enter command (device command): ").strip().lower()
        if user_input.startswith("garage ") or user_input.startswith("fan "):
            parts = user_input.split()
            if len(parts) == 2:
                device, command = parts[0], parts[1]
                valid_commands = {
                    "garage": ["open", "close", "off"],
                    "fan": ["on", "off"]
                }
                if command in valid_commands.get(device, []):
                    if send_data_to_device(device, command):
                        db_ref = db.reference(device)
                        if check_wifi():
                            try:
                                db_ref.update({command: True})
                                # Reset other commands to False
                                if device == "garage":
                                    db_ref.update({cmd: False for cmd in valid_commands["garage"] if cmd != command})
                                elif device == "fan":
                                    db_ref.update({cmd: False for cmd in valid_commands["fan"] if cmd != command})
                            except Exception as e:
                                print(f"Failed to update Firebase: {e}")
                                save_command_locally(device, command)
                                print("Command saved locally due to update failure")
                        else:
                            save_command_locally(device, command)
                            print("WiFi not connected, command saved locally")
                else:
                    print(f"Unknown command for {device}")
            else:
                print("Invalid input format. Use 'device command'.")
        else:
            print("Unknown device. Use 'garage' or 'fan'.")

# I2C LCD setup
I2C_ADDR = 0x3F
LCD_WIDTH = 16
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0
LCD_BACKLIGHT = 0x08
ENABLE = 0b00000100

bus = smbus2.SMBus(1)

def lcd_init():
    try:
        lcd_byte(0x33, LCD_CMD)
        lcd_byte(0x32, LCD_CMD)
        lcd_byte(0x06, LCD_CMD)
        lcd_byte(0x0C, LCD_CMD)
        lcd_byte(0x28, LCD_CMD)
        lcd_byte(0x01, LCD_CMD)
        time.sleep(0.0005)
    except OSError as e:
        print(f"Error initializing LCD: {e}. Check connections and I2C address.")
        exit(1)

def lcd_byte(bits, mode):
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_string(message, line):
    message = message.ljust(LCD_WIDTH, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]), LCD_CHR)

def display_to_lcd(line1, line2):
    lcd_string(line1, LCD_LINE_1)
    lcd_string(line2, LCD_LINE_2)

# Initialize the display
lcd_init()

# Attach listeners to Firebase database
def start_listeners():
    try:
        db_ref_garage.listen(lambda event: firebase_listener(event, "garage"))
        db_ref_fan.listen(lambda event: firebase_listener(event, "fan"))
    except Exception as e:
        print(f"Failed to start listeners: {e}")
        time.sleep(5)  # Wait for 5 seconds before retrying
        start_listeners()  # Retry starting the listeners

# Start a separate thread for terminal input
terminal_thread = threading.Thread(target=terminal_listener)
terminal_thread.daemon = True
terminal_thread.start()

try:
    print("System Initialized")
    display_to_lcd("System Init", "")
    start_listeners()  # Start Firebase listeners
    while True:
        sync_with_firebase()
        time.sleep(10)  # Check WiFi and sync every 10 seconds
except KeyboardInterrupt:
    print("Exiting program")
finally:
    print("Disconnected")
    display_to_lcd("System", "Disconnected")
