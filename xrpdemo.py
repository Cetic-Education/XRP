from XRPLib.defaults import *
from XRPLib.reflectance import Reflectance
import sys
import select
import time

motor1 = EncodedMotor.get_default_encoded_motor(1)
motor2 = EncodedMotor.get_default_encoded_motor(2)

print ("running")
    
def sleep_noblock(ms):
    start = time.ticks_ms()
    while time.ticks_ms() - start < ms:
        pass
    
def set_direction_and_speed(dir1, speed1, dir2, speed2):
    board.led_off()
    motor1._motor.flip_dir = dir1
    motor2._motor.flip_dir = dir2
    motor1.set_speed(speed1)
    motor2.set_speed(speed2)
    sleep_noblock(50)
    board.led_on()

def stop():
    set_direction_and_speed(True, 0, False, 0)
    
def forward(speed = 80):
    set_direction_and_speed(True, speed, False, speed)

def backward(speed = 80):
    set_direction_and_speed(False, speed, True, speed)

def turn_left(speed = 80):
    set_direction_and_speed(False, speed, False, speed)

def turn_right(speed = 80):
    set_direction_and_speed(True, speed, True, speed)
    

board.led_on()
last = ''
while True:

    # Check if there is data to read on stdin
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline().strip()
        if not line:
            continue

        parts = line.split(',')
        command = parts[0]
        speed = 100 # Default speed if not provided
        if len(parts) > 1:
            try:
                speed = int(parts[1])
            except ValueError:
                speed = 100 # Fallback to default

        if last != command:
            stop()
            last = command
            continue
        if command == 'W':
            forward(speed)
        elif command == 'S':
            backward(speed)
        elif command == 'A':
            turn_left(speed)
        elif command == 'D':
            turn_right(speed)
        elif command == 'X': # 'X' is the new command for stop
            stop()
        elif command == 'E': 
            # line_lost_count = 0
            # while line_lost_count <= 20:
            #     if (reflectance.get_left()) <= 0.85 and (reflectance.get_right()) <= 0.85:
            #         forward(80)
            #         line_lost_count = 0 # Reset counter when line is found
            #     else:
            #         stop()
            #         line_lost_count += 1
            #     sleep_noblock(50) # Check sensors more frequently
            stop()
            break

        last = command
