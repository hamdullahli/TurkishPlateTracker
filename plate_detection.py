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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('plate_detection.log')
    ]
)
logger = logging.getLogger(__name__)

class PlateDetector:
    def __init__(self, api_url, api_token):
        """
        Initialize the plate detector
        api_url: URL of the main system's API
        api_token: Token for API authentication
        """
        try:
            self.reader = easyocr.Reader(['tr'])  # Turkish language for license plates
            self.api_url = api_url
            self.api_token = api_token
            logger.info("Plaka algılama sistemi başlatıldı")
        except Exception as e:
            logger.error(f"Başlatma hatası: {str(e)}")
            raise

    def setup_camera(self, camera_id=0, resolution=(1280, 720)):
        """
        Setup camera capture
        camera_id: Camera device ID (default is 0 for primary camera)
        resolution: Desired resolution tuple (width, height)
        """
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                raise Exception(f"Kamera ID {camera_id} açılamadı")

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

            logger.info(f"Kamera başarıyla başlatıldı: ID={camera_id}, Çözünürlük={resolution}")
            return cap
        except Exception as e:
            logger.error(f"Kamera başlatma hatası: {str(e)}")
            raise

    def preprocess_image(self, frame):
        """
        Preprocess the image for better plate detection
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply bilateral filter to remove noise while keeping edges sharp
            bilateral = cv2.bilateralFilter(gray, 11, 17, 17)

            # Edge detection
            edged = cv2.Canny(bilateral, 30, 200)

            return edged
        except Exception as e:
            logger.error(f"Görüntü işleme hatası: {str(e)}")
            return None

    def find_plate_contours(self, processed_img):
        """
        Find contours that might be license plates
        """
        try:
            if processed_img is None:
                return []

            # Find contours
            contours, _ = cv2.findContours(processed_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours based on area and aspect ratio
            possible_plates = []
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h

                # Turkish license plates typically have an aspect ratio between 2 and 5
                if 2.0 <= aspect_ratio <= 5.0 and w > 100:
                    possible_plates.append((x, y, w, h))

            return possible_plates
        except Exception as e:
            logger.error(f"Plaka kontür analizi hatası: {str(e)}")
            return []

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
                "processed_by": "raspberry_pi",
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

    def process_camera_feed(self, camera_id=0, resolution=(1280, 720)):
        """
        Process live camera feed and detect plates
        """
        try:
            cap = self.setup_camera(camera_id, resolution)
            logger.info("Kamera akışı işleniyor...")

            last_detection_time = {}  # Track last detection time for each plate
            min_detection_interval = 5  # Minimum seconds between same plate detections

            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Kameradan görüntü alınamadı")
                    break

                # Process frame
                processed = self.preprocess_image(frame)
                possible_plates = self.find_plate_contours(processed)

                current_time = time.time()

                for plate_roi in possible_plates:
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

                # Add a small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Plaka algılama durduruldu...")
        except Exception as e:
            logger.error(f"Kamera işleme hatası: {str(e)}")
        finally:
            if 'cap' in locals():
                cap.release()

def main():
    # Configuration
    API_URL = os.environ.get("API_URL", "http://0.0.0.0:5000")
    API_TOKEN = os.environ.get("API_TOKEN", "test-token-123")
    CAMERA_ID = int(os.environ.get("CAMERA_ID", "0"))

    # Initialize plate detector
    detector = PlateDetector(API_URL, API_TOKEN)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"Processing RTSP stream: {source}")
            #This part remains untouched as it's not relevant to camera processing.
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                logger.error("Error: Could not open RTSP stream.")
                return

            logger.info("Started processing RTSP stream")

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.error("Error reading frame from stream")
                        break

                    # Process frame
                    processed = detector.preprocess_image(frame)
                    possible_plates = detector.find_plate_contours(processed)

                    for plate_roi in possible_plates:
                        plate_text, confidence = detector.read_plate(frame, plate_roi)

                        if plate_text and confidence > 0.6:  # Minimum confidence threshold
                            logger.info(f"Detected plate: {plate_text} (Confidence: {confidence:.2f})")
                            detector.send_plate_to_server(plate_text, confidence)

                    # Add a small delay to prevent excessive CPU usage
                    time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info("Stopping plate detection...")
            finally:
                cap.release()

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

                    processed = detector.preprocess_image(frame)
                    possible_plates = detector.find_plate_contours(processed)

                    logger.debug(f"Found {len(possible_plates)} possible plate regions")

                    for plate_roi in possible_plates:
                        plate_text, confidence = detector.read_plate(frame, plate_roi)
                        if plate_text and confidence > 0.6:
                            logger.info(f"Detected plate: {plate_text} (Confidence: {confidence:.2f})")
                            try:
                                result = detector.send_plate_to_server(plate_text, confidence)
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
        # Process camera feed by default
        detector.process_camera_feed(camera_id=CAMERA_ID)


if __name__ == "__main__":
    main()