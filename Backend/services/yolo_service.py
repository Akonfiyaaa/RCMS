from ultralytics import YOLO

model = YOLO(r"D:\Ahad\Final_year_project\Yolo_model\Trained_model\yolov8n2\weights\best.pt")

def process_image(file):
    results = model(file.file)
    
    # extract severity + confidence
    return {
        "severity": 0.8,
        "confidence": 0.9
    }