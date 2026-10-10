from django.test import TestCase
from django.urls import reverse

from accounts.test_utils import RolesDataMixin
from projects.models import Project


class ProjectAccessTests(RolesDataMixin, TestCase):
    def test_anonymous_is_redirected_to_login(self):
        url = reverse("projects:list")
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_anonymous_cannot_use_manager_only_pages(self):
        # ManagerRequiredMixin использует raise_exception=True, поэтому и аноним получает 403
        for name, args in [("projects:create", ()), ("projects:edit", (self.project.pk,)),
                           ("projects:delete", (self.project.pk,))]:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)

    def test_everyone_logged_in_sees_list_and_detail(self):
        for user in (self.manager, self.alice, self.carol):
            with self.subTest(user=user.username):
                self.login_as(user)
                self.assertEqual(self.client.get(reverse("projects:list")).status_code, 200)
                self.assertEqual(
                    self.client.get(reverse("projects:detail", args=[self.project.pk])).status_code, 200
                )

    def test_employee_gets_403_on_manager_only_pages(self):
        self.login_as(self.alice)
        for name, args in [("projects:create", ()), ("projects:edit", (self.project.pk,)),
                           ("projects:delete", (self.project.pk,))]:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)

    def test_employee_cannot_create_edit_or_delete_via_post(self):
        self.login_as(self.alice)
        r = self.client.post(reverse("projects:create"), {"title": "Hack", "description": ""})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Project.objects.filter(title="Hack").exists())

        r = self.client.post(reverse("projects:edit", args=[self.project.pk]),
                             {"title": "Hacked", "description": ""})
        self.assertEqual(r.status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Проект A")

        r = self.client.post(reverse("projects:delete", args=[self.other_project.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.other_project.pk).exists())

    def test_manager_can_create_edit_and_delete(self):
        self.login_as(self.manager)

        r = self.client.post(reverse("projects:create"), {"title": "New project", "description": "d"})
        self.assertRedirects(r, reverse("projects:list"))
        self.assertTrue(Project.objects.filter(title="New project").exists())

        r = self.client.post(reverse("projects:edit", args=[self.project.pk]),
                             {"title": "Renamed", "description": ""})
        self.assertRedirects(r, reverse("projects:list"))
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Renamed")

        r = self.client.post(reverse("projects:delete", args=[self.other_project.pk]))
        self.assertRedirects(r, reverse("projects:list"))
        self.assertFalse(Project.objects.filter(pk=self.other_project.pk).exists())