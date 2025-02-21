from datetime import datetime

class PlateRecord:
    def __init__(self, plate_number, confidence, timestamp=None):
        self.plate_number = plate_number
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self):
        return {
            'plate_number': self.plate_number,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }
