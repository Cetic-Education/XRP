import cv2
import serial
import time
import math
import serial.tools.list_ports
import threading
from simple_pid import PID


# Below are helper function that doesn't included in the sylabus of workshop
g_uart = None
g_current_yaw = 0.0
g_lock = threading.Lock()

COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    "yellow": [((20, 43, 46), (30, 255, 255))],
    "purple": [((140, 43, 46), (160, 255, 255))],
}
TARGET_COLOR = "green"
TARGET_SHAPE = "circle"

def serial_reader_thread():
    global g_uart, g_current_yaw, g_lock
    print("Serial reader thread started...")
    while True:
        try:
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
    # [TODO 1] write the logic to create a color mask
    pass

def get_shape_name(contour):
    # [TODO 2] write the logic to determine the shape
    # Hint: use cv2.approxPolyDP
    return "unknown"

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
        # --- 6.3: Start background reading thread ---
    reader_thread = threading.Thread(target=serial_reader_thread, daemon=True)
    reader_thread.start()
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        frame_center_x = width // 2
        reference_line_y = int(height * 0.8)
        # [TODO 3] image preprocessing (Blur, HSV)
        
        # [TODO 4] get Mask
        
        # [TODO 5] draw contours and results
        
        cv2.imshow("Robot Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
