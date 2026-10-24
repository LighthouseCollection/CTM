from django.test import SimpleTestCase


class ClientRouteTests(SimpleTestCase):
    def test_deep_links_serve_the_universal_shell(self):
        for path in ("/cases/example/reports", "/sessions", "/settings/users"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="ctm-root"')
                self.assertIn("no-store", response["Cache-Control"])
