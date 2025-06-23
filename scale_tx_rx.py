import serial
import time
import re

def get_weight():
    port = "/dev/ttyUSB0"
    baud_rate = 9600
    command = "P\r\n"  # "P<cr><lf>"
    
    try:
        with serial.Serial(port, baud_rate, timeout=1) as ser:
            while True:
                user_input = input("Enter command to get weight (or 'exit' to quit): ")
                if user_input.lower() == 'exit':
                    break
                elif user_input.lower() == 'p':
                    ser.write(command.encode('ascii'))  # Send command
                    time.sleep(0.1)  # Give it a moment to respond
                    response = ser.read_until(b'\r\n').decode('ascii').strip()
                    
                    # Extract weight and unit using regex
                    match = re.search(r'([±]?)\s*(\d+\.\d+)\s*(\w)', response)
                    if match:
                        sign = match.group(1)
                        weight = match.group(2)
                        unit = match.group(3)
                        print(f"Weight: {sign}{weight} {unit}")
                    else:
                        print("Invalid response format:", response)
                else:
                    print("Invalid command. Enter 'p' to get weight or 'exit' to quit.")
    except serial.SerialException as e:
        print("Serial error:", e)

if __name__ == "__main__":
    get_weight()
