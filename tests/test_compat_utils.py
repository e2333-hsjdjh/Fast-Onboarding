import unittest

from utils import DeepSeekConfig, UsageLimiter


class CompatUtilsTest(unittest.TestCase):
    def test_old_utils_package_still_reexports_core_types(self):
        self.assertEqual(DeepSeekConfig(api_key="x").model, "deepseek-chat")
        self.assertTrue(UsageLimiter)


if __name__ == "__main__":
    unittest.main()
