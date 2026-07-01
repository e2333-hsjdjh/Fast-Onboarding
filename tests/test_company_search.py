import tempfile
import unittest

from fast_onboarding.intelligence.company_search import CompanyInfoSearch, DuckDuckGoHtmlProvider


class CompanySearchTest(unittest.TestCase):
    def test_parses_search_results_and_archives_payload(self):
        html = """
        <a rel="nofollow" class="result__a" href="https://example.com">Example <b>Company</b></a>
        <a class="result__snippet">A useful snippet about recruiting.</a>
        """

        provider = DuckDuckGoHtmlProvider(http_get=lambda url, headers, timeout: html)
        with tempfile.TemporaryDirectory() as tmp:
            search = CompanyInfoSearch(provider=provider, archive_root=tmp)
            payload = search.search_company("Example", focus_terms=["招聘"], summarize=False)
            self.assertEqual(payload["results"][0]["title"], "Example Company")
            self.assertIn("招聘", payload["query"])
            path = search.archive(payload)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
