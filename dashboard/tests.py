from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.test_utils import RolesDataMixin
from tasks.models import Task


def as_dict(rows):
    return {row["label"]: row["count"] for row in rows}


class DashboardStatsTests(RolesDataMixin, TestCase):
    def test_requires_login(self):
        url = reverse("dashboard:home")
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_manager_sees_stats_for_all_tasks(self):
        self.login_as(self.manager)
        context = self.client.get(reverse("dashboard:home")).context
        self.assertEqual(context["total_tasks"], 4)
        self.assertEqual(as_dict(context["status_stats"]), {
            Task.Status.NEW.label: 2, Task.Status.IN_PROGRESS.label: 1, Task.Status.DONE.label: 1,
        })
        self.assertEqual(as_dict(context["priority_stats"]), {
            Task.Priority.HIGH.label: 1, Task.Priority.MEDIUM.label: 2, Task.Priority.LOW.label: 1,
        })

    def test_employee_sees_stats_only_for_own_tasks(self):
        self.login_as(self.alice)
        context = self.client.get(reverse("dashboard:home")).context
        self.assertEqual(context["total_tasks"], 2)
        self.assertEqual(as_dict(context["status_stats"]), {
            Task.Status.NEW.label: 1, Task.Status.IN_PROGRESS.label: 0, Task.Status.DONE.label: 1,
        })

    def test_employee_without_tasks_gets_zeros(self):
        self.login_as(self.carol)
        context = self.client.get(reverse("dashboard:home")).context
        self.assertEqual(context["total_tasks"], 0)
        self.assertEqual(context["overdue_count"], 0)

    def test_overdue_counts_only_unfinished_tasks_with_past_deadline(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        common = dict(project=self.project, author=self.manager, assignee=self.alice)
        Task.objects.create(title="Overdue open", status=Task.Status.IN_PROGRESS, deadline=yesterday, **common)
        Task.objects.create(title="Overdue done", status=Task.Status.DONE, deadline=yesterday, **common)
        Task.objects.create(title="In future", status=Task.Status.NEW,
                            deadline=today + timedelta(days=5), **common)

        for user, expected in ((self.alice, 1), (self.manager, 1), (self.bob, 0)):
            with self.subTest(user=user.username):
                self.login_as(user)
                context = self.client.get(reverse("dashboard:home")).context
                self.assertEqual(context["overdue_count"], expected)