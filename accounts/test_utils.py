from django.contrib.auth.models import Group, User

from accounts.permissions import EMPLOYEES_GROUP, MANAGERS_GROUP
from projects.models import Project
from tasks.models import Task

PASSWORD = "TestPass123!"


def _create_employee(username, group):
    user = User.objects.create_user(username, password=PASSWORD)
    user.groups.add(group)
    return user


class RolesDataMixin:
    """
    Общие тестовые данные: руководитель, три сотрудника, два проекта, четыре задачи.

    alice_task           автор alice,   исполнитель alice  (Новая,    Средний)
    bob_task             автор manager, исполнитель bob    (В работе, Высокий)
    alice_assigned_task  автор manager, исполнитель alice  (Готово,   Средний)
    unassigned_task      автор manager, исполнителя нет    (Новая,    Низкий)
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        managers, _ = Group.objects.get_or_create(name=MANAGERS_GROUP)
        employees, _ = Group.objects.get_or_create(name=EMPLOYEES_GROUP)

        cls.manager = User.objects.create_user("test_manager", password=PASSWORD)
        cls.manager.groups.add(managers)
        cls.alice = _create_employee("alice", employees)
        cls.bob = _create_employee("bob", employees)
        cls.carol = _create_employee("carol", employees)  # у неё нет задач

        cls.project = Project.objects.create(title="Проект A")
        cls.other_project = Project.objects.create(title="Проект B")

        cls.alice_task = Task.objects.create(
            title="Alice task", project=cls.project,
            author=cls.alice, assignee=cls.alice,
            status=Task.Status.NEW, priority=Task.Priority.MEDIUM,
        )
        cls.bob_task = Task.objects.create(
            title="Bob task", project=cls.project,
            author=cls.manager, assignee=cls.bob,
            status=Task.Status.IN_PROGRESS, priority=Task.Priority.HIGH,
        )
        cls.alice_assigned_task = Task.objects.create(
            title="Assigned to Alice", project=cls.project,
            author=cls.manager, assignee=cls.alice,
            status=Task.Status.DONE, priority=Task.Priority.MEDIUM,
        )
        cls.unassigned_task = Task.objects.create(
            title="Unassigned task", project=cls.project,
            author=cls.manager, assignee=None,
            status=Task.Status.NEW, priority=Task.Priority.LOW,
        )

    def login_as(self, user):
        self.assertTrue(self.client.login(username=user.username, password=PASSWORD))