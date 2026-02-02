import cv2
from ultralytics import YOLO
 
model = YOLO("best.pt")
cap = cv2.VideoCapture(0)
 
cv2.namedWindow("My AI Camera", cv2.WINDOW_NORMAL)
cv2.resizeWindow("My AI Camera", 800, 600)
while True:
    ret, frame = cap.read()
 
    if not ret:
        break
 
    results = model.predict(source=frame, conf=0.5)
    annotated_frame = results[0].plot()
    
    cv2.imshow("My AI Camera", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
cap.release()
cv2.destroyAllWindows()