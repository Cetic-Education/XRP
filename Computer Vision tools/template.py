import cv2
import serial
import time
import math
import serial.tools.list_ports
from simple_pid import PID 

# =========================================
# Global Variables & Constants
# =========================================
uart = None

# [Tip] HSV Color Ranges
COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    # [TODO] Add more colors if needed
}

TARGET_COLOR = "green"
TARGET_SHAPE = "circle"
MAX_EFFORT = 0.9
SEARCH_TURN_EFFORT = 0.5
# =========================================
# Helper Functions (Infrastructure)
# =========================================

def send_command(cmd_type, arg1, arg2, timeout=5.0):
    """
    Send command to pico (Driver Code - Provided)
    
    Args:
    - cmd_type: 'A' (Arcade), 'S' (Straight), 'T' (Turn), 'E' (Exit)
    - arg1: throttle (A), distance (S), degrees (T)
    - arg2: turn (A), speed (S), speed (T)
    """
    command_str = ""
    if cmd_type == 'A':
        command_str = f"A,{arg1:.2f},{arg2:.2f}\n"
    elif cmd_type == 'S':
        command_str = f"S,{arg1:.2f},{arg2:.2f}\n"
    elif cmd_type == 'T':
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
            
            # Non-blocking read for Arcade to clear buffer
            if cmd_type == 'A':
                if uart.in_waiting > 0:
                    raw_data = uart.read(uart.in_waiting)
                    try:
                        msg = raw_data.decode('utf-8').strip()
                        if msg:
                            pass
                            # print(f"[Pico Feedback]: {msg}")
                    except:
                        pass

            # Blocking wait for Straight/Turn
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

    except Exception as e:
        print(f"UART Error: {e}")

def find_uart(baudrate=115200, timeout=1, write_timeout=100):
    """
    Auto-detect and connect to the robot (Provided)
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        try:
            # You might want to filter by "USB" or "Pico" here if needed
            uart = serial.Serial(port.device, baudrate, timeout=timeout, write_timeout=write_timeout)
            time.sleep(2) 
            print(f"Connected to UART on {port.device}")
            uart.reset_input_buffer()
            return uart
        except serial.SerialException:
            continue
    print("Warning: No UART device found. Running in Vision-Only mode.")
    return None

# =========================================
# Student Implementation Area
# =========================================

def create_color_mask(hsv_frame, color_name):
    """
    [TODO 1] Create a mask for the specified color.
    Hint: 
    1. Look up the range in COLOR_RANGE
    2. Use cv2.inRange(hsv_frame, lower, upper)
    3. If a color has 2 ranges (like red), use cv2.bitwise_or to combine them.
    """
    pass

def get_shape_name(contour):
    """
    [TODO 2] Determine the shape of the contour.
    Hint:
    1. Calculate perimeter using cv2.arcLength
    2. Approximate polygon using cv2.approxPolyDP
    3. Count vertices (len(approx)) to decide triangle/rect/circle
    """
    return "unknown"

if __name__ == "__main__":
    
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    
    # 1. Setup Connection
    try:
        # uart = find_uart()
        pass
    except Exception as e:
        print(f"Connection Error: {e}")

    # 2. Setup PID Controllers
    # [TODO] Tune these Kp, Ki, Kd values!
    # Tip: Start with small Kp (e.g., 0.002), Keep Ki/Kd 0 initially.
    turn_pid = PID(Kp=0.002, Ki=0.001, Kd=0.0001, setpoint=0, output_limits=(-MAX_EFFORT, MAX_EFFORT))
    distance_pid = PID(Kp=0.002, Ki=0.001, Kd=0.0001, setpoint=0, output_limits=(-MAX_EFFORT, MAX_EFFORT))

    # 3. Setup Camera
    cap = cv2.VideoCapture(0)
    # Lower resolution for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    print("Starting Robot Vision... Press 'q' to exit.")
    
    aligned_frames_counter = 0
    End = False
    while not End:
        ret, frame = cap.read()
        if not ret: break

        # Resize and get dimensions
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        height, width, _ = frame.shape
        frame_center_x = width // 2
        reference_line_y = int(height * 0.8) # The "Goal" line

        # ---------------------------------------------------------
        # [TODO 3] Image Preprocessing
        # 1. Apply Gaussian Blur to reduce noise (cv2.GaussianBlur)
        # 2. Convert BGR image to HSV (cv2.cvtColor)
        # ---------------------------------------------------------
        # blurred = ...
        # hsv = ...
        
        # ---------------------------------------------------------
        # [TODO 4] Create Mask & Find Contours
        # 1. Call create_color_mask()
        # 2. Call cv2.findContours()
        # ---------------------------------------------------------
        # mask = ...
        # contours, _ = ... (use your create_color_mask function)

        target_found_this_frame = False
        offset_x = 0
        offset_y = 0
        
        best_target_contour = None
        max_area = 0

        # if mask is not None:
            # for contour in contours:# ---------------------------------------------------------
                # [TODO 5] Contour Filtering & Selection
                # 1. Draw ALL contours first (cv2.rectangle in RED)
                # 2. Filter by Size
                # 3. Filter by Shape
                # 4. If Target Found:
                #       -> Calculate offset_x, offset_y
                #       -> Set target_found_this_frame = True
                #       -> Draw GREEN box
                
                #       [Visualization - Provided for you]
                #       Uncomment below after you calculated object_center_x, object_bottom_y
                
                #       base_pt = (frame_center_x, reference_line_y)
                #       corner_pt = (object_center_x, reference_line_y)
                #       end_pt = (object_center_x, object_bottom_y)
                #       cv2.line(frame, base_pt, corner_pt, (255, 0, 0), 3) # Blue: Turn Error
                #       cv2.line(frame, corner_pt, end_pt, (0, 0, 255), 3) # Red: Distance Error
                #       cv2.line(frame, base_pt, end_pt, (0, 255, 255), 1) # Yellow: Direct Path
                #       cv2.putText(frame, f"X:{offset_x}", (x, y-25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)
                #       cv2.putText(frame, f"Y:{offset_y}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
                #       break
                # ---------------------------------------------------------
                # pass
            
        throttle = 0.0
        turn = 0.0
        
        # ---------------------------------------------------------
        # [TODO 6] Visual Servoing Logic (Control Loop)
        # Use the offsets to control the robot
        # ---------------------------------------------------------
        if target_found_this_frame:
            turn_deadzone = 0
            distance_deadzone = 0
            # 1. Calculate PID output
            # turn = turn_pid(offset_x)
            # throttle = distance_pid(offset_y)
            
            # 2. [Optional] Apply "Zig-Zag" or "Mixed Control" logic
            # scale_factor = ... /or
            
            # Example Logic Hint:
            # if abs(offset_x) > TURN_DEADZONE:
            #     turn = turn_pid(offset_x)
            # ...
            
            # 3. Send Command
            # send_command('A', throttle, turn)
            pass # Remove this pass when implemented
            
        else:
            # [TODO] What should the robot do if no target is found?
            # Stop? Spin and search?
            send_command('A', 0, 0) # Currently stops

        # Display Result
        cv2.imshow("Robot Vision", frame)
        # cv2.imshow("Mask", mask) # Optional: Show mask for debugging

        if cv2.waitKey(1) & 0xFF == ord('q'):
            End = True

    # Cleanup
    send_command('E', 0, 0)
    cap.release()
    cv2.destroyAllWindows()
    if uart: uart.close()