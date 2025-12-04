import cv2
import numpy as np

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

cap = cv2.VideoCapture(0)
cv2.namedWindow("Color Picker")
cv2.setMouseCallback("Color Picker", mouse_callback)

mouse_x, mouse_y = 0, 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    height, width, _ = frame.shape
    if 0 <= mouse_x < width and 0 <= mouse_y < height:
        b, g, r = frame[mouse_y, mouse_x]

        h, s, v = hsv_frame[mouse_y, mouse_x]
        
        rgb_text = f"RGB: ({r}, {g}, {b})"
        hsv_text = f"HSV: ({h}, {s}, {v})"
        
        cv2.rectangle(frame, (mouse_x + 10, mouse_y - 40), (mouse_x + 250, mouse_y + 10), (0, 0, 0), -1)
        cv2.putText(frame, rgb_text, (mouse_x + 15, mouse_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, hsv_text, (mouse_x + 15, mouse_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
  
        cv2.circle(frame, (mouse_x, mouse_y), 5, (0, 255, 0), 2)

    cv2.imshow("Color Picker", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()