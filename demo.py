import cv2
import serial
import time
import math
import serial.tools.list_ports
import threading
from simple_pid import PID 

g_uart = None
g_current_yaw = 0.0
g_lock = threading.Lock()
g_end = False

COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    "yellow": [((20, 43, 46), (30, 255, 255))],
    "purple": [((140, 43, 46), (160, 255, 255))],
}
TARGET_COLOR = "green"
TARGET_SHAPE = "circle"
SEARCH_TURN_SPEED_CM_S = 5.5

def serial_reader_thread():
    global g_uart, g_current_yaw, g_lock, g_end
    print("Serial reader thread started...")
    while True:
        try:
            if g_end == True:
                    return
            line = g_uart.readline().decode('utf-8').strip()
            if line.startswith("IMU,"):
                parts = line.split(',')
                if len(parts) == 2:
                    yaw_value = float(parts[1])
                    with g_lock:
                        g_current_yaw = yaw_value
        except (serial.SerialException, ValueError, AttributeError, TypeError) as e:
            print(f"Serial reader thread error or stopped. {e}")
            break
        except Exception as e:
            print(f"Serial reader unknown error: {e}")


def send_command(left_speed_cm_s, right_speed_cm_s):
    global g_uart, g_lock
    
    command_str = f"L,{left_speed_cm_s:.2f},R,{right_speed_cm_s:.2f}\n"
    
    try:
        with g_lock:
            if g_uart and g_uart.is_open:
                g_uart.write(command_str.encode('utf-8'))
                # print(f"Sent: {command_str.strip()}")
    except serial.SerialTimeoutException:
        print("Write timeout occurred")
    except Exception as e:
        print(f"Error sending command: {e}")

# Find and connect to the UART device
def find_uart(baudrate=9600,timeout=1,write_timeout=100):
    ports = serial.tools.list_ports.comports()
    for port in ports:
        try:
            uart = serial.Serial(port.device, baudrate, timeout=timeout, write_timeout=write_timeout)
            time.sleep(2)  # Wait for the connection to establish
            print(f"Connected to UART on {port.device}")
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
            
            # 從 rect 中獲取寬高
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
    
    FRAME_WIDTH = 1920
    FRAME_HEIGHT = 1080
    
    try:
        g_uart = find_uart()
    except serial.SerialException as e:
        print(f"error: {e}")
        exit(1)


    MAX_SPEED_CM_S = 20.0
    
    # PID for Turning (Trying using pid to turn)
    # input: offset_x (from, -960 to +960)
    # output: turn_speed (cm/s, -MAX_SPEED_CM_S to +MAX_SPEED_CM_S)
    # est.: 300 pixels of error -> 10 cm/s turning speed => kp = 10 / 300 = 0.033
    turn_pid = PID(
        Kp=0.05, Ki=0.09, Kd=0.005, 
        setpoint=0, 
        output_limits=(-MAX_SPEED_CM_S, MAX_SPEED_CM_S)
    )

    # PID for Distance (視覺 PID)
    # input: offset_y (pixels)
    # output: base_speed (cm/s, -MAX_SPEED_CM_S to +MAX_SPEED_CM_S)
    # est.: 300 pixels of error -> 15 cm/s forward speed => kp = 15 / 300 = 0.05
    distance_pid = PID(
        Kp=0.05, Ki=0.09, Kd=0.009,
        setpoint=0,
        output_limits=(-MAX_SPEED_CM_S, MAX_SPEED_CM_S)
    )

    # PID for Heading Hold (IMU 航向 PID) 
    # input: current_yaw (degrees)
    # output: correction_speed (cm/s, -10 to +10)
    # est.: 10 degrees of error -> 5 cm/s correction speed => kp = 5 / 10 = 0.5
    heading_pid = PID(
        Kp=0.5, Ki=0.1, Kd=0.05, 
        setpoint=0, # We will set this to the current heading when we start correcting
        output_limits=(-MAX_SPEED_CM_S / 2, MAX_SPEED_CM_S / 2) # Correction speed doesn't need to be too large
    )

    # --- 6.2: Initialize camera ---
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (FRAME_WIDTH, FRAME_HEIGHT))

    # --- 6.3: Start background reading thread ---
    reader_thread = threading.Thread(target=serial_reader_thread, daemon=True)
    reader_thread.start()

    aligned_frames_counter = 0
    End = False
    time.sleep(2) # Wait for camera
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

        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = create_color_mask(hsv, TARGET_COLOR)

        if mask is None: 
            continue
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_found_this_frame = False
        offset_x = 0
        offset_y = 0

        for contour in contours:
            if cv2.contourArea(contour) < 3500:
                continue
            shape = get_shape_name(contour)
            
            if shape == TARGET_SHAPE:
                target_found_this_frame = True
                x, y, w, h = cv2.boundingRect(contour)
                object_center_x = x + w // 2
                object_bottom_y = y + h
                offset_x = object_center_x - frame_center_x
                offset_y = object_bottom_y - reference_line_y
                true_center_y = y + h // 2

                cv2.circle(frame, (object_center_x, true_center_y), 5, (255, 0, 255), -1)

                cv2.putText(frame, "Center", (object_center_x - 25, true_center_y - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.line(frame, (object_center_x, 0), (object_center_x, height), (255, 0, 0), 2)
                cv2.line(frame, (0, reference_line_y), (width, reference_line_y), (0, 255, 255), 2)
                break
        
        # --- PID decision logic ---
        
        with g_lock:
            local_current_yaw = g_current_yaw

        base_speed = 0.0
        turn_speed = 0.0

        if target_found_this_frame:
            # deadzone
            turn_deadzone = 40
            distance_deadzone = 20

            if abs(offset_x) > turn_deadzone:
                # State 1: Need to turn to align (Vision PID)
                turn_speed = -turn_pid(offset_x) # Negative because offset_x > 0 (on the right) needs "turn right"
                
                # Reset heading PID because we are actively turning
                # And set the "target heading" to the new heading we have turned to
                heading_pid.setpoint = local_current_yaw 
                distance_pid.reset()
                aligned_frames_counter = 0

            elif abs(offset_y) > distance_deadzone:
                # 1. Distance PID calculates base forward/backward speed
                base_speed = distance_pid(offset_y) # Negative because offset_y > 0 (too close) -> move backward
                
                # 2. Heading PID calculates correction speed based on "IMU error"
                correction_speed = heading_pid(local_current_yaw)
                turn_speed = correction_speed # Turn speed = heading correction speed
                
                turn_pid.reset()
                aligned_frames_counter = 0
            
            else:
                # State 3: Perfect alignment
                base_speed = 0.0
                turn_speed = 0.0
                # Reset all PIDs
                turn_pid.reset()
                heading_pid.reset()
                distance_pid.reset()
                
                aligned_frames_counter += 1
                print(f"aligning: {aligned_frames_counter}")
                if aligned_frames_counter >= 10:
                    print("Aligned! Sending 'E' command.")
                    End = True # Trigger end
                    
        else:
            # State 4: Target not found
            base_speed = 0.0
            turn_speed = SEARCH_TURN_SPEED_CM_S
            turn_pid.reset()
            heading_pid.reset()
            distance_pid.reset()
            aligned_frames_counter = 0
            
        # --- 6.6: Mix and send commands ---
        
        if not End:
            # Mix "forward" and "turn" speeds (differential drive)
            final_left_speed = base_speed + turn_speed
            final_right_speed = base_speed - turn_speed
            
            send_command(final_left_speed, final_right_speed)
        
        out.write(frame)
        cv2.imshow("Frame", frame) # Open display for debugging

        if cv2.waitKey(1) & 0xFF == ord('q'):
            End = True

    # --- 6.7: Cleanup ---
    print("Task finished. Exiting.")
    send_command(0, 0)
    time.sleep(0.1)
    with g_lock:
        g_end = True
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    if g_uart and g_uart.is_open:
        try:
            g_uart.write("E\n".encode('utf-8'))
            time.sleep(0.1)
            reader_thread.join()
        except Exception as e:
            print(f"Error encountered: {e}")
        finally:
            g_uart.close()
            print("UART connection closed.") 
