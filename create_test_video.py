import cv2
import numpy as np

# Create a video writer
out = cv2.VideoWriter('test_video.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (800, 600))

# Create a sample plate image
img = np.ones((600, 800, 3), dtype=np.uint8) * 255
cv2.putText(img, "34 ABC 123", (300, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
cv2.rectangle(img, (250, 250), (550, 350), (0, 0, 0), 2)

# Write the same frame multiple times to create a video
for _ in range(90):  # 3 seconds at 30 fps
    out.write(img)

out.release()
