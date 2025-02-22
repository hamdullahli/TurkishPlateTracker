import random
import string
import cv2
import numpy as np
import easyocr
import requests
import logging
import time
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateDetector:
    def __init__(self, api_url, username, password):
        """
        Initialize the plate detector
        api_url: URL of the main system's API
        username: Username for API authentication
        password: Password for API authentication
        """
        self.reader = easyocr.Reader(['tr'])  # Turkish language for license plates
        self.api_url = api_url
        self.auth = (username, password)

    def preprocess_image(self, frame):
        """
        Preprocess the image for better plate detection
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to remove noise while keeping edges sharp
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)

        # Edge detection
        edged = cv2.Canny(bilateral, 30, 200)

        return edged

    def find_plate_contours(self, processed_img):
        """
        Find contours that might be license plates
        """
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

    def read_plate(self, img, roi):
        """
        Use EasyOCR to read text from the plate region
        """
        x, y, w, h = roi
        plate_img = img[y:y+h, x:x+w]

        # Görüntü ön işleme
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # Use EasyOCR to read the text
        results = self.reader.readtext(thresh)
        
        # Debug için görüntüyü kaydet
        cv2.imwrite('debug_plate.jpg', thresh)

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

    def send_plate_to_server(self, plate_number, confidence):
        """
        Send detected plate to the main system
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/plates",
                json={"plate_number": plate_number, "confidence": confidence * 100},
                auth=self.auth
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Plate {plate_number} sent to server: {result}")
            return result
        except Exception as e:
            logger.error(f"Error sending plate to server: {e}")
            return None

    def process_rtsp_stream(self, rtsp_url):
        """
        Process RTSP stream and detect plates
        """
        logger.info(f"Trying to connect to RTSP stream: {rtsp_url}")
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            logger.error("Error: Could not open RTSP stream.")
            return

        # Set video capture properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 15)

        logger.info("Started processing RTSP stream")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Error reading frame from stream")
                    break

                # Process frame
                processed = self.preprocess_image(frame)
                possible_plates = self.find_plate_contours(processed)

                for plate_roi in possible_plates:
                    plate_text, confidence = self.read_plate(frame, plate_roi)

                    if plate_text and confidence > 0.6:  # Minimum confidence threshold
                        logger.info(f"Detected plate: {plate_text} (Confidence: {confidence:.2f})")
                        self.send_plate_to_server(plate_text, confidence)

                # Add a small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Stopping plate detection...")
        finally:
            cap.release()

def main():
    # Configuration
    API_URL = "http://0.0.0.0:5000"  # Updated to use 0.0.0.0 instead of localhost
    USERNAME = "admin"  # API username
    PASSWORD = "admin123"  # API password

    # Initialize plate detector
    detector = PlateDetector(API_URL, USERNAME, PASSWORD)

    # Check command line arguments for video file or RTSP URL
    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('rtsp://'):
            logger.info(f"Processing RTSP stream: {source}")
            detector.process_rtsp_stream(source)
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
        logger.error("Please provide a video file path or RTSP URL")
        logger.info("Usage: python plate_detection.py <video_file_or_rtsp_url>")
        logger.info("Example: python plate_detection.py test_video.mp4")
        logger.info("Example: python plate_detection.py rtsp://username:password@camera_ip:554/stream")

if __name__ == "__main__":
    main()