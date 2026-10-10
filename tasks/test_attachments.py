import shutil
import tempfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.test_utils import RolesDataMixin

# Отдельная временная папка: настоящая папка media/ тестами не затрагивается
TEMP_MEDIA = tempfile.mkdtemp()


def read_body(response):
    """Прочитать потоковый ответ и закрыть файл (важно для Windows)."""
    try:
        return b"".join(response.streaming_content)
    finally:
        response.close()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TaskAttachmentAccessTests(RolesDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.alice_task.attachment.save("secret.txt", ContentFile(b"alice secret"), save=True)
        cls.bob_task.attachment.save("bob.txt", ContentFile(b"bob secret"), save=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def _url(self, task):
        return reverse("tasks:attachment", args=[task.pk])

    def test_owner_can_download_file(self):
        self.login_as(self.alice)
        response = self.client.get(self._url(self.alice_task))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(read_body(response), b"alice secret")

    def test_employee_gets_404_for_foreign_attachment(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get(self._url(self.bob_task)).status_code, 404)

    def test_manager_can_download_any_attachment(self):
        self.login_as(self.manager)
        for task, content in ((self.alice_task, b"alice secret"), (self.bob_task, b"bob secret")):
            with self.subTest(task=task.title):
                response = self.client.get(self._url(task))
                self.assertEqual(read_body(response), content)

    def test_anonymous_is_redirected_to_login(self):
        url = self._url(self.alice_task)
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_task_without_attachment_returns_404(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get(self._url(self.alice_assigned_task)).status_code, 404)

    def test_pages_do_not_expose_direct_media_urls(self):
        self.login_as(self.alice)
        for name in ("tasks:detail", "tasks:edit"):
            with self.subTest(url=name):
                response = self.client.get(reverse(name, args=[self.alice_task.pk]))
                self.assertContains(response, self._url(self.alice_task))
                self.assertNotContains(response, settings.MEDIA_URL)
