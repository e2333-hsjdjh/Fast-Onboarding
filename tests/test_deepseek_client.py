import json
import unittest

from utils.config import DeepSeekConfig
from utils.deepseek_client import DeepSeekClient


class DeepSeekClientTest(unittest.TestCase):
    def test_chat_uses_openai_compatible_endpoint(self):
        calls = []

        def fake_post(url, headers, body, timeout):
            calls.append((url, headers, json.loads(body), timeout))
            return {"choices": [{"message": {"content": "ok"}}]}

        client = DeepSeekClient(
            DeepSeekConfig(api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-chat"),
            http_post=fake_post,
        )

        self.assertEqual(client.complete_text("sys", "hello"), "ok")
        url, headers, body, timeout = calls[0]
        self.assertEqual(url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        self.assertEqual(body["model"], "deepseek-chat")
        self.assertEqual(timeout, 30)


if __name__ == "__main__":
    unittest.main()
