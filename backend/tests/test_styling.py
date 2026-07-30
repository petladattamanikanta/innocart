import unittest
from app.services.styling_service import hex_to_hsl, classify_facial_hex

class TestStylingService(unittest.TestCase):
    def test_hex_to_hsl_conversion(self):
        h, s, l = hex_to_hsl("#FFFFFF")
        self.assertEqual(l, 255)
        
        h, s, l = hex_to_hsl("#C8A882")
        self.assertTrue(0 <= h <= 360)
        self.assertTrue(0 <= s <= 100)
        self.assertTrue(0 <= l <= 255)

    def test_classify_facial_hex_fallback(self):
        zones = [
            {"undertone_label": "Warm-Golden", "lum_min": 40, "lum_max": 220, "hue_min": 10, "hue_max": 40, "sat_min": 15, "sat_max": 75, "priority": 1}
        ]
        self.assertEqual(classify_facial_hex("", zones), "Neutral-Beige")

if __name__ == '__main__':
    unittest.main()
