from scriptengine import *
'''
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Objects           | Description                                                                                                                                                                |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| system            | Access to general CODESYS functionalities, such as:                                                                                                                        |
|                   | * Exiting CODESYS                                                                                                                                                          |
|                   | * Handling the general user interface                                                                                                                                      |
|                   | * Access to the message memory (including compiler messages)                                                                                                               |
|                   | * Control of delay and progress bars                                                                                                                                       |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| projects          | Access to the CODESYS project as an object tree that combines the three navigator views (devices, POUs, modules) in one project tree.                                      |
|                   | Also allows for the loading, creating, saving, and closing of projects.                                                                                                    |
|                   | For most objects in a project, there are special methods with detailed functionality, for example compiling, access to ST POUs, export, import, device configuration, etc. |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| online            | Access to online functionalities, such as:                                                                                                                                 |
|                   | * Login to devices and applications                                                                                                                                        |
|                   | * Management of access data (user name, password)                                                                                                                          |
|                   | * Performance of network scans                                                                                                                                             |
|                   | * Gateway management                                                                                                                                                       |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| librarymanager    | Permits the management of library repositories and viewing, installation, and removal of libraries.                                                                        |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| device_repository | Handling of device repositories; import and export of device descriptions.                                                                                                 |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| modulerepository  | Management of CODESYS Application Composer modules and CODESYS Application Composer repositories.                                                                          |
+-------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
'''

import serial
import time
import re

log_file = "/home/waterarc/python/weight_log.txt"
last_weight_file = "/dev/shm/last_weight"  # Use shared memory

def log_message(message):
    with open(log_file, "a") as f:  # Append to full log
        f.write(message + "\n")

    with open(last_weight_file, "w") as f:  # Store last weight in shared memory
        f.write(message)

def get_weight():
    port = "/dev/ttyUSB0"
    baud_rate = 9600
    command = "P\r\n"

    try:
        with serial.Serial(port, baud_rate, timeout=1) as ser:
            ser.write(command.encode('ascii'))
            time.sleep(0.1)
            response = ser.read_until(b'\r\n').decode('ascii').strip()

            match = re.search(r'([±+ -]?)\s*(\d+\.\d+)\s*(\w)', response)
            if match:
                sign = match.group(1).strip()
                weight = match.group(2).strip()
                unit = match.group(3).strip()

                result = f"{weight}".strip()
            else:
                result = f"Invalid response: {response}"

            print(f"Decoded Weight: {result}")
            log_message(result)  # Log result
    except Exception as e:
        log_message(f"Error: {e}")

if __name__ == "__main__":
    get_weight()
