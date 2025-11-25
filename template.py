import cv2
import numpy as np

COLOR_RANGE = {
    "red": [((0, 43, 46), (10, 255, 255)), ((156, 43, 46), (180, 255, 255))],
    "green": [((35, 43, 46), (99, 255, 255))],
    "blue": [((100, 43, 46), (130, 255, 255))],
    "yellow": [((20, 43, 46), (30, 255, 255))],
    "purple": [((140, 43, 46), (160, 255, 255))],
}

def create_color_mask(hsv_frame, color_name):
    # [TODO 1] write the logic to create a color mask
    pass

def get_shape_name(contour):
    # [TODO 2] write the logic to determine the shape
    # Hint: use cv2.approxPolyDP
    return "unknown"

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        # [TODO 3] image preprocessing (Blur, HSV)
        
        # [TODO 4] get Mask
        
        # [TODO 5] draw contours and results
        
        cv2.imshow("Robot Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
