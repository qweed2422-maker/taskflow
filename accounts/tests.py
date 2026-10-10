from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.test import TestCase

from accounts.permissions import is_employee, is_manager
from accounts.test_utils import PASSWORD, RolesDataMixin
from projects.models import Project
from tasks.models import Comment, Task

FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "db.json"


class RoleHelperTests(RolesDataMixin, TestCase):
    def test_manager_group_member_is_manager(self):
        self.assertTrue(is_manager(self.manager))
        self.assertFalse(is_employee(self.manager))

    def test_superuser_is_manager(self):
        root = User.objects.create_superuser("root", password=PASSWORD)
        self.assertTrue(is_manager(root))

    def test_employee_is_not_manager(self):
        self.assertFalse(is_manager(self.alice))
        self.assertTrue(is_employee(self.alice))

    def test_user_without_group_is_not_manager(self):
        nobody = User.objects.create_user("nogroup", password=PASSWORD)
        self.assertFalse(is_manager(nobody))

    def test_anonymous_has_no_role(self):
        anonymous = AnonymousUser()
        self.assertFalse(is_manager(anonymous))
        self.assertFalse(is_employee(anonymous))


class DemoFixtureTests(TestCase):
    """Проверяем fixtures/db.json так, как его загрузит новый пользователь:
    чистая база после migrate, затем loaddata."""

    EMPLOYEES = ["employee1", "employee2", "employee3", "employee4"]

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", str(FIXTURE_PATH), verbosity=0)

    def test_roles(self):
        manager = User.objects.get(username="manager")
        self.assertTrue(is_manager(manager))
        for username in self.EMPLOYEES:
            with self.subTest(username=username):
                user = User.objects.get(username=username)
                self.assertTrue(is_employee(user))
                self.assertFalse(user.is_staff)

    def test_amount_and_variety_of_data(self):
        self.assertEqual(Project.objects.count(), 4)
        self.assertEqual(Task.objects.count(), 14)
        self.assertGreater(Comment.objects.count(), 0)
        self.assertEqual(
            set(Task.objects.values_list("status", flat=True)),
            {s.value for s in Task.Status},
        )
        self.assertEqual(
            set(Task.objects.values_list("priority", flat=True)),
            {p.value for p in Task.Priority},
        )

    def test_credentials_from_readme_work(self):
        self.assertTrue(self.client.login(username="manager", password="Manager2026!"))
        for username in self.EMPLOYEES:
            with self.subTest(username=username):
                self.assertTrue(self.client.login(username=username, password="Employee2026!"))

    def test_demo_employees_see_only_part_of_tasks(self):
        total = Task.objects.count()
        for username in self.EMPLOYEES:
            with self.subTest(username=username):
                user = User.objects.get(username=username)
                visible = Task.objects.visible_to(user)
                self.assertGreater(visible.count(), 0)
                self.assertLess(visible.count(), total)
                for task in visible:
                    self.assertIn(user.pk, (task.author_id, task.assignee_id))