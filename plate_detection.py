import cv2
import numpy as np
import easyocr
import requests
import logging
import time
import sys
import os
from datetime import datetime
from tflite_runtime.interpreter import Interpreter
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('plate_detection.log')
    ]
)
logger = logging.getLogger(__name__)

# Nesne sınıfları (COCO veri setinden)
COCO_LABELS = {
    0: 'background', 1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle',
    5: 'airplane', 6: 'bus', 7: 'train', 8: 'truck', 9: 'boat'
}

class PlateDetector:
    def __init__(self, api_url, api_token, model_path='model/plate_detect_edgetpu.tflite'):
        """
        Initialize the plate detector with Edge TPU support
        api_url: URL of the main system's API
        api_token: Token for API authentication
        model_path: Path to the Edge TPU compatible TFLite model
        """
        try:
            # Initialize EasyOCR for text recognition
            self.reader = easyocr.Reader(['tr'])
            self.api_url = api_url
            self.api_token = api_token

            # Initialize Edge TPU interpreter
            logger.info(f"TPU modelini yükleme deneniyor: {model_path}")
            self.interpreter = edgetpu.make_interpreter(model_path)
            self.interpreter.allocate_tensors()

            # Get model details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.input_shape = self.input_details[0]['shape']

            logger.info("TPU destekli plaka algılama sistemi başlatıldı")
            logger.info(f"Model giriş boyutu: {self.input_shape}")
        except Exception as e:
            logger.error(f"TPU başlatma hatası: {str(e)}")
            raise

    def preprocess_image_for_tpu(self, frame):
        """
        Preprocess image for TPU inference
        """
        try:
            # Resize image to match model input shape
            input_shape = self.input_shape[1:3]
            processed_img = cv2.resize(frame, input_shape)

            # Convert BGR to RGB
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

            # Add batch dimension and convert to float32
            processed_img = np.expand_dims(processed_img, axis=0)
            processed_img = processed_img.astype('float32')

            return processed_img
        except Exception as e:
            logger.error(f"Görüntü ön işleme hatası: {str(e)}")
            return None

    def detect_plate_with_tpu(self, frame):
        """
        Detect vehicles using Edge TPU and then find license plates
        """
        try:
            # Preprocess image
            input_data = self.preprocess_image_for_tpu(frame)
            if input_data is None:
                return []

            logger.debug("TPU inference başlatılıyor")
            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)

            # Run inference
            self.interpreter.invoke()

            # Get detection results
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

            # Filter detections by confidence threshold and vehicle classes
            valid_detections = []
            height, width = frame.shape[:2]
            vehicle_classes = [2, 3, 4, 6, 8]  # bicycle, car, motorcycle, bus, truck

            for i, (box, class_id, score) in enumerate(zip(boxes, classes, scores)):
                if score > 0.5 and int(class_id) in vehicle_classes:
                    logger.debug(f"Araç tespit edildi: {COCO_LABELS[int(class_id)]}, güven: {score:.2f}")

                    # Get vehicle region
                    ymin, xmin, ymax, xmax = box
                    xmin = int(xmin * width)
                    xmax = int(xmax * width)
                    ymin = int(ymin * height)
                    ymax = int(ymax * height)

                    # Extract vehicle region
                    vehicle_region = frame[ymin:ymax, xmin:xmax]
                    if vehicle_region.size == 0:
                        continue

                    # Process vehicle region for plate detection
                    gray = cv2.cvtColor(vehicle_region, cv2.COLOR_BGR2GRAY)
                    gray = cv2.bilateralFilter(gray, 11, 17, 17)
                    edged = cv2.Canny(gray, 30, 200)

                    # Find contours in the edge image
                    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                    # Sort contours by area and keep the largest ones
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

                    for contour in contours:
                        # Approximate the contour
                        peri = cv2.arcLength(contour, True)
                        approx = cv2.approxPolyDP(contour, 0.018 * peri, True)

                        if len(approx) == 4:  # Plaka genellikle 4 köşeli bir dikdörtgendir
                            x, y, w, h = cv2.boundingRect(contour)
                            aspect_ratio = float(w)/h

                            # Türk plakalarının en-boy oranı genellikle 2 ile 5 arasındadır
                            if 2.0 <= aspect_ratio <= 5.0:
                                # Global koordinatlara dönüştür
                                x_global = x + xmin
                                y_global = y + ymin
                                valid_detections.append((x_global, y_global, w, h))

            return valid_detections

        except Exception as e:
            logger.error(f"TPU algılama hatası: {str(e)}")
            return []

    def process_camera_feed(self, camera_id=0, resolution=(1280, 720)):
        """
        Process live camera feed and detect plates using Edge TPU
        """
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                raise Exception(f"Kamera ID {camera_id} açılamadı")

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

            logger.info("TPU destekli kamera akışı başlatıldı")

            last_detection_time = {}  # Track last detection time for each plate
            min_detection_interval = 5  # Minimum seconds between same plate detections

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Kameradan görüntü alınamadı")
                    break

                # Detect plates using TPU
                plate_regions = self.detect_plate_with_tpu(frame)
                current_time = time.time()

                for plate_roi in plate_regions:
                    x, y, w, h = plate_roi
                    plate_img = frame[y:y+h, x:x+w]

                    # Read plate text
                    try:
                        plate_text, confidence = self.read_plate(plate_img)
                        if plate_text and confidence > 0.6:
                            # Check if we recently detected this plate
                            if plate_text in last_detection_time:
                                time_since_last = current_time - last_detection_time[plate_text]
                                if time_since_last < min_detection_interval:
                                    continue

                            logger.info(f"Plaka tespit edildi: {plate_text} (Güven: {confidence:.2f})")
                            self.send_plate_to_server(plate_text, confidence, camera_id)
                            last_detection_time[plate_text] = current_time

                            # Draw detection on frame
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, plate_text, (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    except Exception as e:
                        logger.error(f"Plaka okuma hatası: {str(e)}")
                        continue

                # Add a small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Plaka algılama durduruldu...")
        except Exception as e:
            logger.error(f"Kamera işleme hatası: {str(e)}")
        finally:
            if 'cap' in locals():
                cap.release()

    def read_plate(self, img):
        """
        Use EasyOCR to read text from the plate region
        """
        try:
            if img is None or img.size == 0:
                return None, 0

            # Use EasyOCR to read the text
            results = self.reader.readtext(img)

            if not results:
                return None, 0

            # Get the text with highest confidence
            text = ""
            confidence = 0
            for (_, plate_text, conf) in results:
                # Remove spaces and convert to uppercase
                cleaned_text = "".join(plate_text.split()).upper()
                if conf > confidence:
                    text = cleaned_text
                    confidence = conf

            return text, confidence
        except Exception as e:
            logger.error(f"Plaka okuma hatası: {str(e)}")
            return None, 0

    def send_plate_to_server(self, plate_number, confidence, camera_id=None):
        """
        Send detected plate to the main system
        """
        try:
            data = {
                "plate_number": plate_number,
                "confidence": confidence * 100,
                "processed_by": "tpu_detector",
                "camera_id": camera_id
            }

            response = requests.post(
                f"{self.api_url}/api/plates",
                json=data,
                headers={'X-API-Token': self.api_token}
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Plaka sunucuya gönderildi: {plate_number} ({result})")
            return result
        except Exception as e:
            logger.error(f"Sunucuya gönderme hatası: {str(e)}")
            return None

def main():
    # Configuration
    API_URL = os.environ.get("API_URL", "http://0.0.0.0:5000")
    API_TOKEN = os.environ.get("API_TOKEN", "test-token-123")
    CAMERA_ID = int(os.environ.get("CAMERA_ID", "0"))
    MODEL_PATH = os.environ.get("TPU_MODEL_PATH", "model/plate_detect_edgetpu.tflite")

    # Initialize TPU-enabled plate detector
    logger.info(f"PlateDetector başlatılıyor... Model: {MODEL_PATH}")
    detector = PlateDetector(API_URL, API_TOKEN, model_path=MODEL_PATH)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"RTSP akışı işleniyor: {source}")
            detector.process_camera_feed(source)
        else:
            logger.info(f"Video dosyası işleniyor: {source}")
            detector.process_camera_feed(source)
    else:
        # Process camera feed by default
        detector.process_camera_feed(camera_id=CAMERA_ID)

if __name__ == "__main__":
    main()