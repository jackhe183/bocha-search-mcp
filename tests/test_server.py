import unittest

import server


class ServerToolDescriptionTests(unittest.TestCase):
    def test_registered_tools_have_agent_oriented_descriptions(self):
        tools = server.server._tool_manager._tools

        self.assertEqual(
            sorted(tools.keys()),
            [
                "bocha_ai_search",
                "bocha_fund_remaining",
                "bocha_rerank",
                "bocha_web_search",
            ],
        )
        self.assertIn("WebSearch/WebFetch", tools["bocha_web_search"].description)
        self.assertIn("structured", tools["bocha_ai_search"].description)
        self.assertIn("does not search the web", tools["bocha_rerank"].description)
        self.assertIn("402/403", tools["bocha_fund_remaining"].description)


if __name__ == "__main__":
    unittest.main()
