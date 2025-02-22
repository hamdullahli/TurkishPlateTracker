import cv2
import numpy as np
import easyocr
import requests
import logging
import time
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('plate_detection.log')
    ]
)
logger = logging.getLogger(__name__)

# TPU imports with error handling
try:
    from tflite_runtime.interpreter import Interpreter
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    from pycoral.adapters import detect
    TPU_AVAILABLE = True
    logger.info("TPU bağımlılıkları başarıyla yüklendi")
except ImportError as e:
    TPU_AVAILABLE = False
    logger.error(f"TPU bağımlılıkları yüklenemedi: {str(e)}")
    logger.error("Lütfen setup_tpu.sh betiğini çalıştırın")

# Nesne sınıfları (COCO veri setinden)
COCO_LABELS = {
    0: 'background', 1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle',
    5: 'airplane', 6: 'bus', 7: 'train', 8: 'truck', 9: 'boat'
}

class PlateDetector:
    def __init__(self, api_url, api_token):
        """
        Initialize the plate detector with Edge TPU support
        """
        try:
            logger.info("Plaka tanıma sistemi başlatılıyor...")

            # Initialize EasyOCR for text recognition
            logger.info("EasyOCR başlatılıyor...")
            self.reader = easyocr.Reader(['tr'])

            self.api_url = api_url
            self.api_token = api_token

            if not TPU_AVAILABLE:
                raise ImportError("TPU bağımlılıkları eksik")

            # Initialize Edge TPU for vehicle detection
            logger.info("TPU modelini yükleme deneniyor...")
            model_path = os.path.join('model', 'ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite')

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"TPU modeli bulunamadı: {model_path}")

            try:
                self.interpreter = edgetpu.make_interpreter(model_path)
                self.interpreter.allocate_tensors()

                # Get model details
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                self.input_shape = self.input_details[0]['shape']

                logger.info("TPU destekli plaka algılama sistemi başlatıldı")
                logger.info(f"Model giriş boyutu: {self.input_shape}")

            except Exception as tpu_error:
                logger.error(f"TPU başlatma hatası: {str(tpu_error)}")
                raise

        except Exception as e:
            logger.error(f"Başlatma hatası: {str(e)}")
            raise

    def preprocess_image(self, frame):
        """
        Preprocess image for TPU inference
        """
        try:
            if frame is None:
                raise ValueError("Geçersiz frame")

            # Resize image to match model input shape
            input_shape = self.input_shape[1:3]
            processed_img = cv2.resize(frame, input_shape)

            # Convert BGR to RGB
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

            # Add batch dimension and convert to uint8
            processed_img = np.expand_dims(processed_img, axis=0)

            return processed_img

        except Exception as e:
            logger.error(f"Görüntü ön işleme hatası: {str(e)}")
            return None

    def detect_vehicles(self, frame):
        """
        Detect vehicles using Edge TPU
        """
        try:
            # Preprocess image
            input_data = self.preprocess_image(frame)
            if input_data is None:
                return []

            # Run inference
            try:
                self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
                self.interpreter.invoke()

                # Get detection results
                boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
                classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
                scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

            except Exception as tpu_error:
                logger.error(f"TPU çıkarım hatası: {str(tpu_error)}")
                return []

            # Filter vehicle detections
            height, width = frame.shape[:2]
            vehicle_classes = [2, 3, 4, 6, 8]  # bicycle, car, motorcycle, bus, truck
            vehicles = []

            for i, (box, class_id, score) in enumerate(zip(boxes, classes, scores)):
                if score > 0.5 and int(class_id) in vehicle_classes:
                    ymin, xmin, ymax, xmax = box
                    xmin = max(0, int(xmin * width))
                    xmax = min(width, int(xmax * width))
                    ymin = max(0, int(ymin * height))
                    ymax = min(height, int(ymax * height))

                    vehicles.append({
                        'box': (xmin, ymin, xmax - xmin, ymax - ymin),
                        'score': score,
                        'class': COCO_LABELS[int(class_id)]
                    })

                    logger.debug(f"Araç tespit edildi: {COCO_LABELS[int(class_id)]}, güven: {score:.2f}")

            return vehicles

        except Exception as e:
            logger.error(f"Araç tespiti hatası: {str(e)}")
            return []

    def process_camera_feed(self, camera_id=0):
        """
        Process camera feed and detect plates
        """
        try:
            logger.info(f"Kamera akışı başlatılıyor: {camera_id}")

            # Handle RTSP URLs
            if isinstance(camera_id, str) and camera_id.startswith('rtsp://'):
                logger.info("RTSP bağlantısı tespit edildi")
                cap = cv2.VideoCapture(camera_id)
                if not cap.isOpened():
                    raise Exception(f"RTSP bağlantısı başarısız: {camera_id}")
            else:
                # Try to convert to integer for regular camera
                try:
                    camera_id = int(camera_id)
                except ValueError:
                    logger.warning(f"Kamera ID'si sayıya çevrilemedi, orijinal değer kullanılıyor: {camera_id}")
                cap = cv2.VideoCapture(camera_id)
                if not cap.isOpened():
                    raise Exception(f"Kamera bağlantısı başarısız: {camera_id}")

            # Track last detection time for each plate
            last_detection_time = {}
            min_detection_interval = 5  # Minimum seconds between same plate detections

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Kameradan frame alınamadı")
                    break

                # Detect vehicles
                vehicles = self.detect_vehicles(frame)

                current_time = time.time()
                for vehicle in vehicles:
                    # Find plate candidates in vehicle region
                    plates = self.detect_plate_in_vehicle(frame, vehicle)

                    if not plates:
                        continue

                    for plate in plates:
                        # Read plate text
                        plate_text, confidence = self.read_plate(frame, plate)

                        if plate_text and confidence > 0.6:
                            # Check detection interval
                            if plate_text in last_detection_time:
                                time_since_last = current_time - last_detection_time[plate_text]
                                if time_since_last < min_detection_interval:
                                    continue

                            logger.info(f"Plaka tespit edildi: {plate_text} (Güven: {confidence:.2f})")
                            self.send_plate_to_server(plate_text, confidence)
                            last_detection_time[plate_text] = current_time

                            # Draw detection
                            x, y, w, h = plate['box']
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, plate_text, (x, y-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                time.sleep(0.1)  # CPU kullanımını azalt

        except KeyboardInterrupt:
            logger.info("Kullanıcı tarafından durduruldu")
        except Exception as e:
            logger.error(f"Kamera işleme hatası: {str(e)}")
            raise
        finally:
            if 'cap' in locals():
                cap.release()

    def detect_plate_in_vehicle(self, frame, vehicle):
        """
        Detect license plate within a vehicle region
        """
        try:
            x, y, w, h = vehicle['box']
            vehicle_region = frame[y:y+h, x:x+w]

            if vehicle_region.size == 0:
                return None

            # Convert to grayscale
            gray = cv2.cvtColor(vehicle_region, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, 11, 17, 17)
            edged = cv2.Canny(gray, 30, 200)

            # Find contours
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

            plate_candidates = []
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.018 * peri, True)

                if len(approx) == 4:  # Plaka genellikle 4 köşeli
                    x_plate, y_plate, w_plate, h_plate = cv2.boundingRect(contour)
                    aspect_ratio = float(w_plate)/h_plate

                    # Türk plakalarının en-boy oranı kontrolü
                    if 2.0 <= aspect_ratio <= 5.0:
                        plate_candidates.append({
                            'box': (x + x_plate, y + y_plate, w_plate, h_plate),
                            'confidence': vehicle['score']
                        })

            return plate_candidates

        except Exception as e:
            logger.error(f"Plaka bölgesi tespiti hatası: {str(e)}")
            return None

    def read_plate(self, frame, plate):
        """
        Read text from the plate region using EasyOCR
        """
        try:
            x, y, w, h = plate['box']
            plate_img = frame[y:y+h, x:x+w]

            if plate_img is None or plate_img.size == 0:
                return None, 0

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

    def send_plate_to_server(self, plate_number, confidence):
        """
        Send detected plate to the API server
        """
        try:
            data = {
                "plate_number": plate_number,
                "confidence": confidence * 100,  # Convert to percentage
                "processed_by": "tpu_detector"
            }

            # Log API request
            logger.info(f"Plaka sunucuya gönderiliyor: {plate_number} (Güven: {confidence:.2f})")

            response = requests.post(
                f"{self.api_url}/api/plates",
                json=data,
                headers={'X-API-Token': self.api_token},
                timeout=5  # Add timeout
            )
            response.raise_for_status()
            result = response.json()

            # Log server response
            logger.info(f"Sunucu yanıtı: {result}")

            if result.get('is_authorized'):
                logger.info(f"Plaka yetkili: {plate_number}")
            else:
                logger.info(f"Plaka yetkisiz: {plate_number}")

            return result

        except requests.exceptions.Timeout:
            logger.error("Sunucu yanıt vermedi (timeout)")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Sunucuya gönderme hatası: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {str(e)}")
            return None

def main():
    try:
        # Configuration
        API_URL = os.environ.get("API_URL", "http://localhost:5000")
        API_TOKEN = os.environ.get("API_TOKEN", "test-token-123")

        # Check TPU availability first
        if not TPU_AVAILABLE:
            logger.error("TPU bağımlılıkları eksik. Lütfen setup_tpu.sh betiğini çalıştırın")
            sys.exit(1)

        # Initialize detector
        logger.info(f"API URL: {API_URL}")
        detector = PlateDetector(API_URL, API_TOKEN)

        # Process video source
        if len(sys.argv) > 1:
            source = sys.argv[1]
            logger.info(f"Video kaynağı: {source}")
            detector.process_camera_feed(source)
        else:
            # Use default camera
            detector.process_camera_feed(0)

    except Exception as e:
        logger.error(f"Program hatası: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()