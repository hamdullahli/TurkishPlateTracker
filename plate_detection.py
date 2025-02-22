import cv2
import numpy as np
import easyocr
import requests
import logging
import time
from datetime import datetime
import sys

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PlateDetector:
    def __init__(self, api_url):
        """Initialize the plate detector"""
        self.reader = easyocr.Reader(['tr'])
        self.api_url = api_url
        self.plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')
        logger.info("Plate detector initialized successfully")

    def preprocess_image(self, frame):
        """Görüntü ön işleme"""
        try:
            # Görüntü boyutunu kontrol et ve gerekirse yeniden boyutlandır
            if frame.shape[1] > 1000:
                scale = 1000 / frame.shape[1]
                frame = cv2.resize(frame, None, fx=scale, fy=scale)

            # Gürültü azaltma ve keskinleştirme
            denoised = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

            # Keskinleştirme filtresi
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)

            # Gri tonlamaya çevirme
            gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)

            # Kontrast iyileştirme
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)

            return enhanced
        except Exception as e:
            logger.error(f"Error in preprocess_image: {e}")
            return None

    def detect_plate(self, frame):
        """Plaka tespiti ve OCR"""
        try:
            # Görüntü ön işleme
            processed = self.preprocess_image(frame)
            if processed is None:
                return frame, []

            # Plaka tespiti için cascade classifier
            plates = self.plate_cascade.detectMultiScale(
                processed,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 20),
                maxSize=(300, 100)
            )

            detected_plates = []
            for (x, y, w, h) in plates:
                logger.debug(f"Found potential plate at: x={x}, y={y}, w={w}, h={h}")

                # ROI'yi genişlet
                padding = 10
                roi_y1 = max(y - padding, 0)
                roi_y2 = min(y + h + padding, frame.shape[0])
                roi_x1 = max(x - padding, 0)
                roi_x2 = min(x + w + padding, frame.shape[1])

                roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                if roi.size == 0:
                    continue

                # ROI ön işleme
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, roi_thresh = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # OCR işlemi
                results = self.reader.readtext(roi_thresh)
                if results:
                    best_result = max(results, key=lambda x: x[2])
                    text = best_result[1]
                    conf = best_result[2] * 100

                    # Plaka formatı düzeltme
                    text = text.upper().replace('İ', 'I').replace('Ğ', 'G').replace('Ç', 'C')
                    text = ''.join(c for c in text if c.isalnum())

                    if len(text) >= 5 and any(c.isdigit() for c in text):
                        logger.info(f"Valid plate detected: {text} (Confidence: {conf:.2f}%)")

                        detected_plates.append({
                            'text': text,
                            'confidence': conf,
                            'bbox': (x, y, w, h)
                        })

                        # Görüntü üzerine çizim
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(frame, f"{text} ({conf:.1f}%)", 
                                  (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                                  0.5, (0, 255, 0), 2)

            return frame, detected_plates

        except Exception as e:
            logger.error(f"Error in detect_plate: {e}")
            return frame, []

    def process_rtsp_stream(self, rtsp_url):
        """RTSP akışını işle"""
        logger.info(f"Connecting to RTSP stream: {rtsp_url}")

        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                logger.error("Failed to open RTSP stream")
                return

            # Kamera ayarlarını optimize et
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer size'ı küçült

            last_detection_time = {}  # Aynı plakayı tekrar göndermemek için

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from stream")
                    break

                processed_frame, detected_plates = self.detect_plate(frame)

                current_time = time.time()
                for plate in detected_plates:
                    # Aynı plakayı 5 saniyede bir gönder
                    if (plate['text'] not in last_detection_time or 
                        current_time - last_detection_time[plate['text']] > 5):

                        try:
                            response = requests.post(
                                f"{self.api_url}/api/plates",
                                json={
                                    "plate_number": plate['text'],
                                    "confidence": plate['confidence']
                                }
                            )
                            if response.ok:
                                last_detection_time[plate['text']] = current_time
                                logger.info(f"Plate {plate['text']} sent to server successfully")
                        except Exception as e:
                            logger.error(f"Failed to send plate to server: {e}")

                # Frame'i JPEG formatına dönüştür ve gönder
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                time.sleep(0.1)  # CPU kullanımını azalt

        except Exception as e:
            logger.error(f"Error in process_rtsp_stream: {e}")
        finally:
            if 'cap' in locals():
                cap.release()

def main():
    # Configuration
    API_URL = "http://0.0.0.0:5000"

    # Initialize plate detector
    detector = PlateDetector(API_URL)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"Processing RTSP stream: {source}")
            for frame in detector.process_rtsp_stream(source):
                pass
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

                    time.sleep(0.1)  # CPU kullanımını azalt

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