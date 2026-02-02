from ultralytics import YOLO 

model = YOLO('yolov8n.pt')
results = model.train(
    data='/content/my_yolo_dataset/data.yaml',
    epochs=20,
    imgsz=640
)