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
            self.interpreter = edgetpu.make_interpreter(model_path)
            self.interpreter.allocate_tensors()

            # Get model details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.input_shape = self.input_details[0]['shape']

            logger.info("TPU destekli plaka algılama sistemi başlatıldı")
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

            # Normalize pixel values
            processed_img = processed_img.astype('float32') / 255.0

            # Add batch dimension
            processed_img = np.expand_dims(processed_img, axis=0)

            return processed_img
        except Exception as e:
            logger.error(f"Görüntü ön işleme hatası: {str(e)}")
            return None

    def detect_plate_with_tpu(self, frame):
        """
        Detect license plates using Edge TPU
        """
        try:
            # Preprocess image
            input_data = self.preprocess_image_for_tpu(frame)
            if input_data is None:
                return []

            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)

            # Run inference
            self.interpreter.invoke()

            # Get detection results
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

            # Filter detections by confidence threshold
            valid_detections = []
            height, width = frame.shape[:2]

            for i, score in enumerate(scores):
                if score > 0.5:  # Confidence threshold
                    ymin, xmin, ymax, xmax = boxes[i]
                    xmin = int(xmin * width)
                    xmax = int(xmax * width)
                    ymin = int(ymin * height)
                    ymax = int(ymax * height)
                    valid_detections.append((xmin, ymin, xmax - xmin, ymax - ymin))

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
                    # Extract plate region
                    x, y, w, h = plate_roi
                    plate_img = frame[y:y+h, x:x+w]

                    # Read plate text
                    plate_text, confidence = self.read_plate(frame, plate_roi)

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

                # Add a small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Plaka algılama durduruldu...")
        except Exception as e:
            logger.error(f"Kamera işleme hatası: {str(e)}")
        finally:
            if 'cap' in locals():
                cap.release()

    def read_plate(self, img, roi):
        """
        Use EasyOCR to read text from the plate region
        """
        try:
            x, y, w, h = roi
            plate_img = img[y:y+h, x:x+w]

            # Use EasyOCR to read the text
            results = self.reader.readtext(plate_img)

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
    detector = PlateDetector(API_URL, API_TOKEN, model_path=MODEL_PATH)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"RTSP akışı işleniyor: {source}")
            detector.process_camera_feed(source) #modified to handle RTSP stream directly
        else:
            logger.info(f"Video dosyası işleniyor: {source}")
            detector.process_camera_feed(source) #modified to handle video file directly
    else:
        # Process camera feed by default
        detector.process_camera_feed(camera_id=CAMERA_ID)

if __name__ == "__main__":
    main()