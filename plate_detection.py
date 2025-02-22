import cv2
import numpy as np
import easyocr
import requests
import logging
import time
from datetime import datetime
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateDetector:
    def __init__(self, api_url, username="admin", password="admin123"):
        self.reader = easyocr.Reader(['tr'])
        self.api_url = api_url
        self.auth = (username, password)
        self.plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

    def detect_plate(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        plates = self.plate_cascade.detectMultiScale(gray, 1.1, 4)

        detected_plates = []
        for (x, y, w, h) in plates:
            # Plaka bölgesini genişlet
            roi = frame[max(y-10,0):min(y+h+10,frame.shape[0]), 
                       max(x-10,0):min(x+w+10,frame.shape[1])]

            if roi.size == 0:
                continue

            # Görüntü ön işleme
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # Plaka metnini oku
            results = self.reader.readtext(thresh)

            if results:
                text = max(results, key=lambda x: x[2])[1]
                conf = max(results, key=lambda x: x[2])[2] * 100

                # Sadece geçerli plaka formatındakileri al
                if len(text) >= 5 and any(c.isdigit() for c in text):
                    detected_plates.append({
                        'text': text,
                        'confidence': conf,
                        'bbox': (x, y, w, h)
                    })

                    # Görüntü üzerine çizim
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, text, (x, y-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        return frame, detected_plates

    def send_plate_to_server(self, plate_text, confidence):
        try:
            response = requests.post(
                f"{self.api_url}/api/plates",
                json={"plate_number": plate_text, "confidence": confidence},
                auth=self.auth
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending plate to server: {e}")
            return None

    def process_rtsp_stream(self, rtsp_url):
        logger.info(f"Connecting to stream: {rtsp_url}")
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            logger.error("Could not open video stream")
            return

        last_detection_time = {}  # Aynı plakayı tekrar göndermemek için

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Error reading frame")
                break

            processed_frame, detected_plates = self.detect_plate(frame)

            current_time = time.time()
            for plate in detected_plates:
                # Aynı plakayı 5 saniyede bir gönder
                if (plate['text'] not in last_detection_time or 
                    current_time - last_detection_time[plate['text']] > 5):

                    result = self.send_plate_to_server(plate['text'], plate['confidence'])
                    if result:
                        last_detection_time[plate['text']] = current_time
                        logger.info(f"Plate detected and sent: {plate['text']}")

            # Stream için frame'i döndür
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            time.sleep(0.1)  # CPU kullanımını azalt

        cap.release()

def main():
    # Configuration
    API_URL = "http://0.0.0.0:5000"  
    USERNAME = "admin"  
    PASSWORD = "admin123"  

    # Initialize plate detector
    detector = PlateDetector(API_URL, USERNAME, PASSWORD)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"Processing RTSP stream: {source}")
            for frame in detector.process_rtsp_stream(source):
                # This would typically send the frame to a streaming server
                pass # Placeholder for streaming logic.
        else:
            logger.info(f"Processing video file: {source}")
            try:
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    logger.error(f"Error: Could not open video file {source}")
                    return

                logger.info("Successfully opened video file")

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.info("Reached end of video file")
                        break

                    processed_frame, detected_plates = detector.detect_plate(frame)

                    for plate in detected_plates:
                        logger.info(f"Detected plate: {plate['text']} (Confidence: {plate['confidence']:.2f})")
                        try:
                            result = detector.send_plate_to_server(plate['text'], plate['confidence'])
                            logger.info(f"Server response: {result}")
                        except Exception as e:
                            logger.error(f"Failed to send plate to server: {e}")
                    time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info("Stopping plate detection...")
            except Exception as e:
                logger.error(f"Error processing video: {e}")
            finally:
                cap.release()
    else:
        logger.error("Please provide a video file path or RTSP URL")
        logger.info("Usage: python plate_detection.py <video_file_or_rtsp_url>")
        logger.info("Example: python plate_detection.py test_video.mp4")
        logger.info("Example: python plate_detection.py rtsp://username:password@camera_ip:554/stream")

if __name__ == "__main__":
    main()