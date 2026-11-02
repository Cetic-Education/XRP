import cv2
import serial
import time
import serial.tools.list_ports
from pathlib import Path
from ultralytics import YOLO
from simple_pid import PID 
 
uart = None
 
MODEL_PATH = str(Path(__file__).resolve().parent.parent / "models" / "best.pt")
TARGET_CLASS = "circle"
MODEL_CONF_THRESOLD = 0.45
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
def find_uart(baudrate=115200,timeout=1,write_timeout=1):
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
 
if __name__ == "__main__":
 
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
 
    try:
        uart = find_uart()
    except serial.SerialException as e:
        print(f"error: {e}")
        uart = None
        # exit(1)
 
 
    model = YOLO(MODEL_PATH)
 
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
 
 
        target_found_this_frame = False
        offset_x = 0
        offset_y = 0
 
        best_target_box = None
        best_target_area = 0
 
        try:
            results = model(frame, conf=MODEL_CONF_THRESOLD, verbose=False)
            # print(results[0])
            if results and len(results) > 0:
                for result in results:
                    boxes = result.boxes
                    if boxes is None or len(boxes) == 0:
                        continue
 
                    for box in boxes:
                        cls_id = int(box.cls.item())
                        class_name = model.names.get(cls_id, str(cls_id))
                        if class_name != TARGET_CLASS:
                            continue
 
                        x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                        area = (x2 - x1) * (y2 - y1)
                        if area > best_target_area:
                            best_target_area = area
                            best_target_box = (x1, y1, x2, y2)
        except Exception as exc:
            print(f"Inference error: {exc}")
 
        cv2.line(frame, (frame_center_x, 0), (frame_center_x, height), (255, 0, 0), 2)       # 垂直中線 (X Axis)
        cv2.line(frame, (0, reference_line_y), (width, reference_line_y), (0, 255, 255), 2) # 水平目標線 (Y Axis)
        if best_target_box is not None:
            target_found_this_frame = True
            x1, y1, x2, y2 = [int(v) for v in best_target_box]
            object_center_x = (x1 + x2) / 2.0
            object_bottom_y = float(y2)
 
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
 
            offset_x = object_center_x - frame_center_x
            offset_y = object_bottom_y - reference_line_y
 
            base_pt = (frame_center_x, reference_line_y)
            corner_pt = (int(object_center_x), reference_line_y)
            end_pt = (int(object_center_x), int(object_bottom_y))
 
            cv2.putText(frame, f"X Error: {int(offset_x)}", (x1, max(0, y1 - 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, f"Y Error: {int(offset_y)}", (x1, max(0, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.line(frame, base_pt, corner_pt, (255, 0, 0), 3)
            cv2.line(frame, corner_pt, end_pt, (0, 0, 255), 3)
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
