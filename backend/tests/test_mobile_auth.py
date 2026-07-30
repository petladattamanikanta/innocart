import unittest
from app.services.mobile_service import mobile_service

class TestMobileAuthService(unittest.TestCase):
    def test_register_and_login_timestamp(self):
        email = "testuser_timestamp@example.com"
        password = "Password123!"

        # Register
        reg_res = mobile_service.register_user(
            name="Test User",
            email=email,
            password=password
        )
        self.assertEqual(reg_res["status"], "success")
        self.assertIn("last_login_at", reg_res["user"])
        self.assertIsNotNone(reg_res["user"]["last_login_at"])

        # Login
        login_res = mobile_service.login_user(
            email=email,
            password=password
        )
        self.assertEqual(login_res["status"], "success")
        self.assertIn("last_login_at", login_res["user"])
        self.assertIsNotNone(login_res["user"]["last_login_at"])

        # Get profile
        user_id = login_res["user"]["user_id"]
        profile_res = mobile_service.get_user_profile(user_id)
        self.assertEqual(profile_res["status"], "success")
        profile = profile_res["profile"]
        self.assertIn("last_login_at", profile)

if __name__ == "__main__":
    unittest.main()
