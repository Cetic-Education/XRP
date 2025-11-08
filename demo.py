import cv2
import serial
import time
import math
import serial.tools.list_ports


# --- Part to MODIFY: if more colors are needed, add them here ---
# Define color ranges in HSV, HSV: Hue, Saturation, Value
# As we mainly care about hue for color detection, we set saturation and value to wide ranges and it's not critical here        
COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    "yellow": [((20, 43, 46), (30, 255, 255))],
    "purple": [((140, 43, 46), (160, 255, 255))],
}


# --- Part to MODIFY: Define your target here ---
TARGET_COLOR = "green"
TARGET_SHAPE = "circle"


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

def send_command(cmd, speed=None):
    if speed is not None:
        command_str = f"{cmd},{int(speed)}\n"
    else:
        command_str = f"{cmd}\n"
    try:
        uart.write(command_str.encode('utf-8'))
        print("Sent:", command_str.strip())
    except serial.SerialTimeoutException:
        print("Write timeout occurred")
    except Exception as e:
        print(f"Error sending command: {e}")


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

def calculate_speed(offset, max_offset, min_speed, max_speed, curve_factor=2.0):
    """
    Calculates speed based on offset using a curve.
    A simple quadratic curve: y = ax^2 + b
    """
    if abs(offset) < 20: # Dead zone
        return 0

    # Normalize offset to be between 0 and 1
    normalized_offset = min(abs(offset) / max_offset, 1.0)

    # Apply the curve, the curve helps to have finer control at lower speeds
    curved_offset = pow(normalized_offset, curve_factor)

    # Map the curved offset to the speed range
    speed = min_speed + (max_speed - min_speed) * curved_offset

    return min(speed, max_speed)

if __name__ == "__main__":
    # Initialize UART communication
    
    FRAME_WIDTH=1920
    FRAME_HEIGHT=1080
    uart = None
    
    
    try:
        uart = find_uart()
    except serial.SerialException as e:
        print(f"error: {e}")
        exit(1)

    # Open camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (FRAME_WIDTH, FRAME_HEIGHT))

    # Counter for consecutive aligned frames
    aligned_frames_counter = 0
    End = False

    time.sleep(2)  # Allow camera to warm up
    while not cap.isOpened():
        time.sleep(0.1)

    found = False
    found_false = 0

    while not End:
        ret, frame = cap.read()
        if not ret:
            continue

        
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        height, width, _ = frame.shape
        frame_center_x = width // 2
        reference_line_y = int(height * 0.8)  # 80% down the frame

        # Convert to HSV and mask red
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)


        # 1. Create mask ONLY for the target color
        mask = create_color_mask(hsv, TARGET_COLOR)

        if mask is None:
            # If color is not defined, skip
            continue

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_found_this_frame = False
        command_to_send = ("A", 10) # 'X' for Stop, speed 0

        # 2. Loop through contours of the target color
        for contour in contours:
            # Filter out small noise
            if cv2.contourArea(contour) < 3500:
                continue

            # 3. Check if the shape matches the target shape
            shape = get_shape_name(contour)
            if shape == TARGET_SHAPE:
                target_found_this_frame = True

                x, y, w, h = cv2.boundingRect(contour)
                object_center_x = x + w // 2
                object_bottom_y = y + h
                offset_x = object_center_x - frame_center_x
                offset_y = object_bottom_y - reference_line_y

                # Highlight the found target
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.line(frame, (object_center_x, 0), (object_center_x, height), (255, 0, 0), 2)
                cv2.line(frame, (0, reference_line_y), (width, reference_line_y), (0, 255, 255), 2)

                # --- Speed calculation logic ---
                MIN_SPEED = 5
                MAX_SPEED = 70
            

                # Decision logic
                if abs(offset_x) > 40:
                    # Horizontal movement (turning)
                    
                    turn_speed = calculate_speed(offset_x, frame_center_x, MIN_SPEED, MAX_SPEED)
                    command_to_send = ("D", turn_speed) if offset_x > 0 else ("A", turn_speed)
                    aligned_frames_counter = 0 # Reset counter if not aligned
                elif abs(offset_y) > 20:
                    # Vertical movement (forward/backward)
                    
                    move_speed = calculate_speed(offset_y, height - reference_line_y, MIN_SPEED, MAX_SPEED)
                    command_to_send = ("S", move_speed) if offset_y > 0 else ("W", move_speed)
                    aligned_frames_counter = 0
                else:
                    # Target is aligned
                    aligned_frames_counter += 1
                    if aligned_frames_counter >= 10:
                        print("Aligned for 20 frames! Sending Sprint command.")
                        command_to_send = ("E", MAX_SPEED) # 'E' for Sprint
                        aligned_frames_counter = 0 # Reset counter after sending
                        End = True
                    else:
                        # Aligned, but not for long enough, so just stop and wait
                        print(f"Aligned, waiting... ({aligned_frames_counter}/20)")
                        command_to_send = ("X", 0) # Send Stop command
                command_to_send = ("X",0) if found == False else command_to_send
                found = True
                found_false=0
                # Found and processed the target, no need to check other contours in this frame
                break
        
        if not target_found_this_frame:
            aligned_frames_counter = 0 # Reset counter if target is lost
            found_false+=1
        
        if found_false >= 5:
            found = False
            found_false=0

        send_command(command_to_send[0], command_to_send[1])
        time.sleep(0.1) # Reduced sleep time for faster reaction
        out.write(frame)  # Save frame to video
        cv2.imshow("Frame", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("Task finished. Exiting.")
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    if uart and uart.is_open:
            uart.close()
            print("UART connection closed.")
