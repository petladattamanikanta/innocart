import unittest
import hmac
import hashlib
from app.services.payment_service import PaymentService

class TestPaymentService(unittest.TestCase):
    def test_razorpay_signature_verification(self):
        ps = PaymentService()
        body = b'{"event":"payment.captured"}'
        secret = "secret_innocart_key"
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        self.assertTrue(ps.verify_razorpay_signature(body, expected))
        self.assertFalse(ps.verify_razorpay_signature(body, "invalid_signature"))

if __name__ == '__main__':
    unittest.main()
