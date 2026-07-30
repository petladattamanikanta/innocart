import unittest
from app.services.cart_service import CartSession, CartLine

class TestCartService(unittest.TestCase):
    def test_cart_totals(self):
        session = CartSession(session_id="TEST-001")
        session.lines["SKU-1"] = CartLine(sku="SKU-1", name="Test Shirt", price=999.00, image_url="", quantity=2)
        session.lines["SKU-2"] = CartLine(sku="SKU-2", name="Test Pants", price=1499.00, image_url="", quantity=1)
        
        self.assertEqual(session.item_count, 3)
        self.assertEqual(session.raw_total, 3497.00)
        self.assertEqual(session.cart_total, 3497.00)

    def test_cart_discount_calculation(self):
        session = CartSession(session_id="TEST-002", discount_amount=200.00)
        session.lines["SKU-1"] = CartLine(sku="SKU-1", name="Hoodie", price=2499.00, image_url="", quantity=1)
        
        self.assertEqual(session.raw_total, 2499.00)
        self.assertEqual(session.cart_total, 2299.00)

if __name__ == '__main__':
    unittest.main()
