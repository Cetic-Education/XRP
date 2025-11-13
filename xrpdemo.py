from XRPLib.defaults import *
from XRPLib.imu import IMU
from XRPLib.encoded_motor import EncodedMotor # For importing ZERO_EFFORT_BRAKE
from XRPLib.differential_drive import DifferentialDrive
import sys
import select
import time

print("Running")
imu = IMU.get_default_imu()
drivetrain = DifferentialDrive.get_default_differential_drive()

try:
    imu.calibrate(1)  
    imu.reset_yaw()  
    print("IMU calibrated and reset.")
except Exception as e:
    print(f"IMU init error: {e}")

# drivetrain.set_zero_effort_behavior(EncodedMotor.ZERO_EFFORT_BREAK)
drivetrain.stop()

REPORT_INTERVAL_MS = 50  # 50ms = 20Hz
last_report_time = time.ticks_ms()

board.led_on()

drivetrain.set_speed(0,0)
while True:
    
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline().strip()
        
        if line:
            board.led_off()
            try:
                # [L,speed_cm_s,R,speed_cm_s]'
                parts = line.split(',')
                if parts[0] == 'L' and parts[2] == 'R':
                    left_speed_cm_s = float(parts[1])
                    right_speed_cm_s = float(parts[3])
                    drivetrain.set_speed(left_speed_cm_s, right_speed_cm_s)
                    board.led_on()
                elif line == 'E':
                    drivetrain.stop()
                    break
                    
            except Exception as e:
                drivetrain.stop()
                print("Error parsing command: {}".format(e))

    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_report_time) > REPORT_INTERVAL_MS:
        last_report_time = current_time
        
        print("IMU,{:.2f}\n".format(imu.get_yaw()))

drivetrain.stop()
board.led_off()