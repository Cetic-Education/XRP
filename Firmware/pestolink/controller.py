import sys
import select
import bluetooth
import time
import math
from machine import Pin, ADC
from XRPLib.defaults import *
from XRPLib.imu import IMU
from XRPLib.encoded_motor import EncodedMotor # For importing ZERO_EFFORT_BRAKE
from XRPLib.differential_drive import DifferentialDrive

from pestolink import PestoLinkAgent

ROBOT_NAME = "XRProbot"

BUTTON_ENABLE_AUTO = 1
BUTTON_EMERGENCY_STOP = 2

pestolink = PestoLinkAgent(ROBOT_NAME)
imu.calibrate(1)  
imu.reset_yaw()
drivetrain = DifferentialDrive.get_default_differential_drive()

# Mode definitions
MODE_MANUAL = 0
MODE_AUTO = 1
current_mode = MODE_MANUAL

print(f"System Started. Mode: MANUAL. Waiting for PestoLink...")

def clear_input_buffer():
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        sys.stdin.readline()

def handle_auto_command(line):
    global current_mode
    board.led_on()
    try:
        parts = line.split(',')
        cmd = parts[0].strip().upper()

        if cmd == 'E':
            print("Command: EXIT to Manual")
            return False

        elif cmd == 'A':
            # Arcade: a, throttle, turn
            if len(parts) >= 3:
                throttle = float(parts[1])
                turn = float(parts[2])
                print(f"Command: Arcade T={throttle}, R={turn}")
                drivetrain.arcade(throttle, turn)
            else:
                print("Err")

        elif cmd == 'S':
            # Straight: s, distance, effort
            if len(parts) >= 3:
                dist = float(parts[1])
                effort = float(parts[2])
                print(f"Command: Straight Dist={dist}, Effort={effort}")
                drivetrain.straight(dist, effort)
                print("Done")
            else:
                print("Err")

        elif cmd == 'T':
            # Turn: t, degrees, effort
            if len(parts) >= 3:
                deg = float(parts[1])
                effort = float(parts[2])
                print(f"Command: Turn Deg={deg}, Effort={effort}")
                drivetrain.turn(deg, effort)
                print("Done")
            else:
                print("Err")
        
        else:
            print(f"Unknown command: {cmd}")

    except ValueError as e:
        print(f"Parse Error: {e}")
    except Exception as e:
        print(f"Execution Error: {e}")
    
    return True

while True:
    
    # ------------------------------------------------
    # 1. MANUAL MODE
    # ------------------------------------------------
    if current_mode == MODE_MANUAL:
        if pestolink.is_connected():
            rotation = -1 * pestolink.get_axis(0)
            throttle = -1 * pestolink.get_axis(1)
            drivetrain.arcade(throttle, rotation)
        
            if(pestolink.get_button(0)):
                servo_one.set_angle(110)
            else:
                servo_one.set_angle(90)
                
            # check for AUTO mode button
            if pestolink.get_button(BUTTON_ENABLE_AUTO):
                print("Switching to AUTO Mode...")
                board.led_on()
                drivetrain.stop()
                current_mode = MODE_AUTO
                clear_input_buffer()
                time.sleep(0.5)
                board.led_off()

            batteryVoltage = (ADC(Pin("BOARD_VIN_MEASURE")).read_u16())/(1024*64/14)
            pestolink.telemetryPrintBatteryVoltage(batteryVoltage)
        
        else:
            drivetrain.stop()

    # ------------------------------------------------
    # 2. AUTO MODE
    # ------------------------------------------------
    elif current_mode == MODE_AUTO:
        # Priority 1: Check if "cut off/emergency stop" button is pressed (if Bluetooth is still connected)
        # Note: If executing blocking functions like straight/turn, this won't be executed
        if pestolink.is_connected() and pestolink.get_button(BUTTON_EMERGENCY_STOP):
            print("Emergency STOP triggered by Button!")
            drivetrain.stop()
            current_mode = MODE_MANUAL
            board.led_off()
            time.sleep(0.5)
            continue


        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line:
                # Handle command
                keep_auto = handle_auto_command(line)
                if not keep_auto:
                    # Received 'E' command, switch back to manual
                    drivetrain.stop()
                    current_mode = MODE_MANUAL
                    board.led_off()

    # Sleep a bit to free CPU resources, avoid overheating or high usage
    time.sleep(0.01)