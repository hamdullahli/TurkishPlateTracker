import random
import string

def mock_plate_detection(image_data):
    """
    Mock function to simulate license plate detection
    Returns a tuple of (plate_number, confidence)
    """
    # Generate random Turkish style plate
    city_code = str(random.randint(1, 81)).zfill(2)
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = str(random.randint(100, 999))
    plate = f"{city_code} {letters} {numbers}"
    
    confidence = random.uniform(85.0, 99.9)
    
    return plate, confidence
