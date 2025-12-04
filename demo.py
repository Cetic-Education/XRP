import cv2
import serial
import time
import math
import serial.tools.list_ports
from simple_pid import PID 

uart = None

COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    "yellow": [((20, 43, 46), (30, 255, 255))],
    "purple": [((140, 43, 46), (160, 255, 255))],
}
TARGET_COLOR = "green"
TARGET_SHAPE = "circle"
SEARCH_TURN_EFFORT = 0.66
MAX_EFFORT = 0.95

def send_command(cmd_type, arg1, arg2, timeout=5.0):
    """
    Send command to pico
    
    參數:
    - cmd_type: 'A' (Arcade), 'S' (Straight), 'T' (Turn), 'E' (Exit)
    - arg1: throttle (A), distance (S), degrees (T)
    - arg2: turn (A), speed (S), speed (T)
    - timeout: Max second to run command (available for S and T)
    """
    
    command_str = ""
    if cmd_type == 'A':
        # Arcade: A, throttle, turn
        command_str = f"A,{arg1:.2f},{arg2:.2f}\n"
    elif cmd_type == 'S':
        # Straight: S, distance, speed
        command_str = f"S,{arg1:.2f},{arg2:.2f}\n"
    elif cmd_type == 'T':
        # Turn: T, degrees, speed
        command_str = f"T,{arg1:.2f},{arg2:.2f}\n"
    elif cmd_type == 'E':
        command_str = "E\n"
    else:
        print(f"Error: Unknown command type {cmd_type}")
        return

    try:
        if uart and uart.is_open:
            if cmd_type in ['S', 'T']:
                uart.reset_input_buffer()

            uart.write(command_str.encode('utf-8'))
            if cmd_type == 'A':
                # check accumulating data
                if uart.in_waiting > 0:
                    raw_data = uart.read(uart.in_waiting)
                    try:
                        msg = raw_data.decode('utf-8').strip()
                        if msg:
                            pass
                            # print(f"[Pico Feedback]: {msg}")
                    except:
                        pass

            if cmd_type in ['S', 'T']:
                start_time = time.time()
                
                while (time.time() - start_time) < timeout:
                    if uart.in_waiting:
                        line = uart.readline().decode('utf-8', errors='ignore').strip()
                        
                        if "DONE" in line.upper():
                            # print(f"Command {cmd_type} Completed.") # Debug
                            return
                        
                        if "ERR" in line.upper():
                            print(f"Warning: Robot returned error for {cmd_type}")
                            return

                    time.sleep(0.01)
                
                print(f"Timeout: Did not receive DONE for command {cmd_type}")

    except serial.SerialTimeoutException:
        print("UART Write Timeout")
    except Exception as e:
        print(f"UART Error: {e}")

# Find and connect to the UART device
def find_uart(baudrate=115200,timeout=1,write_timeout=100):
    ports = serial.tools.list_ports.comports()
    for port in ports:
        try:
            uart = serial.Serial(port.device, baudrate, timeout=timeout, write_timeout=write_timeout)
            time.sleep(2)  # Wait for the connection to establish
            print(f"Connected to UART on {port.device}")
            uart.reset_input_buffer()
            return uart
        except serial.SerialException:
            continue
    raise serial.SerialException("No UART device found")

def create_color_mask(hsv_frame, color_name):
    # Creates a mask for a specific color in an HSV frame.
    ranges = COLOR_RANGE.get(color_name.lower())

    if not ranges:
        return None
    
    masks = [cv2.inRange(hsv_frame, lower, upper) for (lower, upper) in ranges]
    
    if len(masks) > 1:
        return cv2.bitwise_or(*masks)
    elif masks:
        return masks[0]
    return None
# here's an alternative function to create color masks for multiple ranges, more straightforward but harder to read
"""
    # Create the first mask
    mask = cv2.inRange(hsv_frame, ranges[0][0], ranges[0][1])

    # If there are more ranges (like for red), combine them
    for i in range(1, len(ranges)):
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv_frame, ranges[i][0], ranges[i][1]))
    return mask
"""

def get_shape_name(contour):
    """
    Analyzes a contour and returns its shape name as a string.
    """
    # Approximate the contour to a polygon
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
    num_vertices = len(approx)

    shape = "unidentified"

    if num_vertices == 3:
        shape = "triangle"
    elif num_vertices == 4:
        # It could be a square or a rectangle
        # Use minAreaRect to get a rotation-invariant bounding box using the original contour
        area = cv2.contourArea(contour)
        rect = cv2.minAreaRect(contour)
        
        # Get box points and calculate box area
        box = cv2.boxPoints(rect)
        box_area = cv2.contourArea(box)
        
        #  Calculate extent, which is the ratio of contour area to bounding box area
        extent = area / box_area if box_area > 0 else 0
        
        if extent > 0.9:
            # when extent is high, we can be more confident about the shape
            # then check aspect ratio
            
            # Get width and height from rect
            (w, h) = rect[1]
            if w > h:
                w, h = h, w
            
            aspect_ratio = h / w if w > 0 else 0
            if 1.0 <= aspect_ratio <= 1.2: # Allow some tolerance
                shape = "square"
            else:
                shape = "rectangle"
    elif num_vertices > 4: # Check for circle
        area = cv2.contourArea(contour)
        (x, y), radius = cv2.minEnclosingCircle(contour)
        if radius > 0:
            circle_area = math.pi * (radius ** 2)
            circularity = area / circle_area
            if 0.76 < circularity < 1.25: # Allow some tolerance
                shape = "circle"
    return shape


if __name__ == "__main__":
    
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    
    try:
        uart = find_uart()
    except serial.SerialException as e:
        print(f"error: {e}")
        # exit(1)


    
    
    # PID for Turning (Trying using pid to turn)
    # input: offset_x (from, -960 to +960)
    # output: turn_speed (cm/s, -MAX_SPEED_CM_S to +MAX_SPEED_CM_S)
    # est.: 300 pixels of error -> 10 cm/s turning speed => kp = 10 / 300 = 0.033
    turn_pid = PID(
        Kp=0.002, Ki=0.001, Kd=0.0001, 
        setpoint=0, 
        output_limits=(-MAX_EFFORT, MAX_EFFORT)
    )

    # PID for Distance (visual PID)
    # input: offset_y (pixels)
    # output: base_speed (cm/s, -MAX_SPEED_CM_S to +MAX_SPEED_CM_S)
    # est.: 300 pixels of error -> 15 cm/s forward speed => kp = 15 / 300 = 0.05
    distance_pid = PID(
        Kp=0.002, Ki=0.001, Kd=0.0001,
        setpoint=0,
        output_limits=(-MAX_EFFORT, MAX_EFFORT)
    )

    # --- 6.2: Initialize camera ---
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (FRAME_WIDTH, FRAME_HEIGHT))

    aligned_frames_counter = 0
    End = False
    while not cap.isOpened():
        time.sleep(0.1)
    
    while not End:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        height, width, _ = frame.shape
        frame_center_x = width // 2
        reference_line_y = int(height * 0.8)

        cv2.line(frame, (frame_center_x, 0), (frame_center_x, height), (255, 0, 0), 2)       # 垂直中線 (X Axis)
        cv2.line(frame, (0, reference_line_y), (width, reference_line_y), (0, 255, 255), 2) # 水平目標線 (Y Axis)
        
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = create_color_mask(hsv, TARGET_COLOR)

        if mask is None: 
            continue
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_found_this_frame = False
        offset_x = 0
        offset_y = 0
        
        best_target_contour = None
        max_area = 0
        
        for contour in contours:
            
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 1)
            area = cv2.contourArea(contour)
            if area < 3500:
                continue
            
            shape = get_shape_name(contour)
            
            if shape == TARGET_SHAPE:
                if area > max_area:
                    max_area = area
                    best_target_contour = contour
        if best_target_contour is not None:
            target_found_this_frame = True
            
            # get bounding box and calculate offsets
            x, y, w, h = cv2.boundingRect(best_target_contour)
            object_center_x = x + w // 2
            object_bottom_y = y + h
            
            # using green thick box to highlight target
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

            # calculate offsets
            offset_x = object_center_x - frame_center_x
            offset_y = object_bottom_y - reference_line_y
            
            # 1. coordinate you want to reach
            base_pt = (frame_center_x, reference_line_y)
            # 2. Corner form object to target pt
            corner_pt = (object_center_x, reference_line_y)
            # Object bottom
            end_pt = (object_center_x, object_bottom_y)
            
            # display coordinate text
            cv2.putText(frame, f"X Error: {offset_x}", (x, y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, f"Y Error: {offset_y}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)     
            # A. X axis offset
            cv2.line(frame, base_pt, corner_pt, (255, 0, 0), 3)
            # B. Y axis offset
            cv2.line(frame, corner_pt, end_pt, (0, 0, 255), 3)
            # C. hypotenuse
            cv2.line(frame, base_pt, end_pt, (0, 255, 255), 1)


        throttle = 0.0
        turn = 0.0

        if target_found_this_frame:
            # deadzone
            turn_deadzone = 40
            distance_deadzone = 20

            turn = turn_pid(offset_x)
            throttle = distance_pid(offset_y)
            
            scale_factor = 1.0 - min(abs(turn) / MAX_EFFORT, 0.8)
            throttle *= scale_factor
            
            if abs(offset_x) <= turn_deadzone and abs(offset_y) <= distance_deadzone:
                turn = 0
                throttle = 0
                
                aligned_frames_counter += 1
                print(f"Aligning: {aligned_frames_counter}")
                if aligned_frames_counter >= 10:
                    print("Aligned! Sending 'E'")
                    End = True
            else:
                aligned_frames_counter = 0
            send_command('A', throttle, turn)
        else:
            send_command('A', 0, SEARCH_TURN_EFFORT) 
            turn_pid.reset()
            distance_pid.reset()
            aligned_frames_counter = 0
            
        
        out.write(frame)
        cv2.imshow("Frame", frame) # Open display for debugging

        if cv2.waitKey(1) & 0xFF == ord('q'):
            End = True

    # --- 6.7: Cleanup ---
    print("Task finished. Exiting.")
    send_command('E', 0, 0)
    time.sleep(0.1)
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    if uart and uart.is_open:
        try:
            uart.write("E\n".encode('utf-8'))
            time.sleep(0.1)
        except Exception as e:
            print(f"Error encountered: {e}")
        finally:
            uart.close()
            print("UART connection closed.") 
