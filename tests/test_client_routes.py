import pytest
from django.test import TestCase


@pytest.fixture(autouse=True)
def published_questionnaires():
    # Shell rendering needs no questionnaire fixtures. On PostgreSQL every request
    # still sets its RLS session settings, so the test case must allow the database.
    pass


class ClientRouteTests(TestCase):
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
