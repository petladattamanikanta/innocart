import unittest
import cv2
import numpy as np
from app.services.cv_service import cv_service

class TestCVService(unittest.TestCase):
    def test_skin_telemetry_extraction(self):
        # Create a synthetic 200x200 BGR face image with warm golden skin RGB (212, 163, 115) -> BGR (115, 163, 212)
        img = np.full((200, 200, 3), (115, 163, 212), dtype=np.uint8)
        
        # Add subtle natural texture variation noise
        noise = np.random.randint(-5, 5, (200, 200, 3)).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Encode to JPEG bytes
        _, buffer = cv2.imencode(".jpg", img)
        image_bytes = buffer.tobytes()

        # Execute CV Analysis
        res = cv_service.analyze_skin_telemetry(image_bytes)
        
        self.assertEqual(res["status"], "success")
        self.assertIn("facial_hex", res)
        self.assertIn("undertone_label", res)
        self.assertIn("skin_texture", res)
        self.assertIn("skin_texture_score", res)
        self.assertGreaterEqual(res["skin_texture_score"], 0.0)
        self.assertLessEqual(res["skin_texture_score"], 1.0)

if __name__ == "__main__":
    unittest.main()
