
import cv2
import numpy as np

# Load model once (important for performance)
model = YOLO(r"D:\Ahad\Final_year_project\Yolo_model\Trained_model\yolov8n2\weights\best.pt")

def process_image(file_bytes):
    # Convert bytes → numpy image
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    h, w, _ = img.shape
    image_area = w * h

    # Run detection
    results = model(img)

    boxes = results[0].boxes.xyxy.cpu().numpy()
    confs = results[0].boxes.conf.cpu().numpy()

    CONF_THRESHOLD = 0.5
    MIN_AREA_RATIO = 0.0005

    final_scores = []

    label_scale = min(w, h) * 0.0025
    label_thickness = max(1, int(round(min(w, h) * 0.005)))
    badge_padding = max(5, int(round(min(w, h) * 0.01)))

    for i, box in enumerate(boxes):
        confidence = confs[i]

        if confidence < CONF_THRESHOLD:
            continue

        x1, y1, x2, y2 = box
        pothole_area = (x2 - x1) * (y2 - y1)

        if pothole_area < MIN_AREA_RATIO * image_area:
            continue

        size_score = pothole_area / image_area
        severity = min(size_score * 5, 1)

        combined = (0.6 * severity) + (0.4 * confidence)
        final_scores.append(combined)

        x1, y1, x2, y2 = map(int, box)

        # Color coding
        if severity < 0.3:
            color = (0, 255, 0)
        elif severity < 0.7:
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)

        cv2.rectangle(img, (x1, y1), (x2, y2), color, label_thickness)

        label = f"C:{confidence:.2f} S:{severity:.2f}"
        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, label_scale, label_thickness)
        text_w, text_h = text_size
        label_top = y1 - text_h - badge_padding * 2
        if label_top < 0:
            label_top = y2 + badge_padding
        cv2.rectangle(img,
                      (x1, label_top),
                      (x1 + text_w + badge_padding * 2, label_top + text_h + badge_padding),
                      color,
                      cv2.FILLED)
        cv2.putText(img,
                    label,
                    (x1 + badge_padding, label_top + text_h + badge_padding // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    label_scale,
                    (255, 255, 255),
                    label_thickness,
                    cv2.LINE_AA)

    # Final score
    if len(final_scores) == 0:
        image_score = 0
    else:
        avg_score = np.mean(final_scores)
        count = len(final_scores)
        count_factor = min(count / 5, 1)

        image_score = round((0.6 * avg_score + 0.8 * count_factor) * 10)
        image_score = min(image_score, 10)

    # Add text
    cv2.putText(img, f"Potholes: {len(final_scores)}",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.putText(img, f"Final Score: {image_score}/10",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Convert image → bytes to send back
    _, buffer = cv2.imencode(".jpg", img)
    image_bytes = buffer.tobytes()

    return {
        "image_bytes": image_bytes,
        "score": image_score,
        "potholes": len(final_scores)
    }
