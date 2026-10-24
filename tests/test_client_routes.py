import pytest
from django.test import SimpleTestCase


@pytest.fixture(autouse=True)
def published_questionnaires():
    # Shell rendering does not use questionnaire or database fixtures.
    pass


class ClientRouteTests(SimpleTestCase):
    def test_deep_links_serve_the_universal_shell(self):
        for path in ("/cases/example/reports", "/sessions", "/settings/users"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="ctm-root"')
                self.assertIn("no-store", response["Cache-Control"])

    def test_unknown_api_and_private_media_paths_remain_not_found(self):
        for path in ("/api/missing-endpoint/", "/media/originals/private.pdf", "/not-a-client-route"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
