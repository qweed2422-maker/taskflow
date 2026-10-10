import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.test_utils import RolesDataMixin
from tasks.models import Comment, Task

TEMP_MEDIA = tempfile.mkdtemp()


def login_redirect(url):
    return f"{reverse('login')}?next={url}"


class TaskListVisibilityTests(RolesDataMixin, TestCase):
    def test_anonymous_is_redirected_to_login(self):
        url = reverse("tasks:list")
        self.assertRedirects(self.client.get(url), login_redirect(url))

    def test_manager_sees_all_tasks(self):
        self.login_as(self.manager)
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(
            set(response.context["tasks"]),
            {self.alice_task, self.bob_task, self.alice_assigned_task, self.unassigned_task},
        )

    def test_employee_sees_only_own_tasks(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(set(response.context["tasks"]), {self.alice_task, self.alice_assigned_task})

    def test_employee_without_tasks_sees_nothing(self):
        self.login_as(self.carol)
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(list(response.context["tasks"]), [])

    def test_search_does_not_leak_foreign_tasks(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:list"), {"q": "Bob"})
        self.assertEqual(list(response.context["tasks"]), [])

    def test_assignee_filter_does_not_leak_foreign_tasks(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:list"), {"assignee": self.bob.pk})
        self.assertEqual(list(response.context["tasks"]), [])

    def test_filter_dropdowns_contain_only_related_users_and_projects(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(list(response.context["assignees"]), [self.alice])
        self.assertEqual(list(response.context["projects"]), [self.project])

    def test_status_filter_works_within_visible_tasks(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:list"), {"status": Task.Status.DONE.value})
        self.assertEqual(list(response.context["tasks"]), [self.alice_assigned_task])


class TaskObjectAccessTests(RolesDataMixin, TestCase):
    def test_employee_can_open_own_and_assigned_tasks(self):
        self.login_as(self.alice)
        for task in (self.alice_task, self.alice_assigned_task):
            with self.subTest(task=task.title):
                response = self.client.get(reverse("tasks:detail", args=[task.pk]))
                self.assertEqual(response.status_code, 200)

    def test_employee_gets_404_for_foreign_and_unassigned_tasks(self):
        self.login_as(self.alice)
        for task in (self.bob_task, self.unassigned_task):
            for name in ("tasks:detail", "tasks:edit"):
                with self.subTest(task=task.title, url=name):
                    response = self.client.get(reverse(name, args=[task.pk]))
                    self.assertEqual(response.status_code, 404)

    def test_employee_cannot_edit_foreign_task_via_post(self):
        self.login_as(self.alice)
        response = self.client.post(
            reverse("tasks:edit", args=[self.bob_task.pk]),
            {"title": "Hacked", "description": "", "status": Task.Status.DONE.value,
             "priority": Task.Priority.LOW.value, "deadline": ""},
        )
        self.assertEqual(response.status_code, 404)
        self.bob_task.refresh_from_db()
        self.assertEqual(self.bob_task.title, "Bob task")
        self.assertEqual(self.bob_task.status, Task.Status.IN_PROGRESS)

    def test_manager_can_open_and_edit_any_task(self):
        self.login_as(self.manager)
        for task in (self.alice_task, self.bob_task, self.unassigned_task):
            for name in ("tasks:detail", "tasks:edit"):
                with self.subTest(task=task.title, url=name):
                    self.assertEqual(self.client.get(reverse(name, args=[task.pk])).status_code, 200)

    def test_anonymous_cannot_open_task(self):
        url = reverse("tasks:detail", args=[self.alice_task.pk])
        self.assertRedirects(self.client.get(url), login_redirect(url))


class TaskEditRulesTests(RolesDataMixin, TestCase):
    def _data(self, **overrides):
        data = {"title": "Alice task", "description": "", "status": Task.Status.NEW.value,
                "priority": Task.Priority.MEDIUM.value, "deadline": ""}
        data.update(overrides)
        return data

    def test_employee_can_change_status_of_own_task(self):
        self.login_as(self.alice)
        url = reverse("tasks:edit", args=[self.alice_task.pk])
        response = self.client.post(url, self._data(status=Task.Status.DONE.value))
        self.assertRedirects(response, reverse("tasks:detail", args=[self.alice_task.pk]))
        self.alice_task.refresh_from_db()
        self.assertEqual(self.alice_task.status, Task.Status.DONE)

    def test_employee_can_edit_task_assigned_to_him(self):
        self.login_as(self.alice)
        url = reverse("tasks:edit", args=[self.alice_assigned_task.pk])
        response = self.client.post(url, self._data(title="Updated", status=Task.Status.IN_PROGRESS.value))
        self.assertEqual(response.status_code, 302)
        self.alice_assigned_task.refresh_from_db()
        self.assertEqual(self.alice_assigned_task.title, "Updated")

    def test_employee_cannot_change_assignee_or_project(self):
        self.login_as(self.alice)
        url = reverse("tasks:edit", args=[self.alice_task.pk])
        data = self._data(assignee=self.bob.pk, project=self.other_project.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.alice_task.refresh_from_db()
        self.assertEqual(self.alice_task.assignee, self.alice)
        self.assertEqual(self.alice_task.project, self.project)

    def test_manager_can_change_assignee_and_project(self):
        self.login_as(self.manager)
        url = reverse("tasks:edit", args=[self.alice_task.pk])
        data = self._data(assignee=self.bob.pk, project=self.other_project.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.alice_task.refresh_from_db()
        self.assertEqual(self.alice_task.assignee, self.bob)
        self.assertEqual(self.alice_task.project, self.other_project)


class TaskCreateRulesTests(RolesDataMixin, TestCase):
    def test_employee_form_has_no_assignee_field(self):
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:create"))
        self.assertNotIn("assignee", response.context["form"].fields)

    def test_manager_form_has_assignee_field(self):
        self.login_as(self.manager)
        response = self.client.get(reverse("tasks:create"))
        self.assertIn("assignee", response.context["form"].fields)

    def test_employee_becomes_author_and_cannot_assign(self):
        self.login_as(self.alice)
        response = self.client.post(reverse("tasks:create"), {
            "title": "From Alice", "description": "", "priority": Task.Priority.HIGH.value,
            "project": self.project.pk, "deadline": "", "assignee": self.bob.pk,
        })
        task = Task.objects.get(title="From Alice")
        self.assertRedirects(response, reverse("tasks:detail", args=[task.pk]))
        self.assertEqual(task.author, self.alice)
        self.assertIsNone(task.assignee)

    def test_manager_can_create_task_with_assignee(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("tasks:create"), {
            "title": "From manager", "description": "", "status": Task.Status.NEW.value,
            "priority": Task.Priority.LOW.value, "assignee": self.bob.pk,
            "project": self.project.pk, "deadline": "",
        })
        task = Task.objects.get(title="From manager")
        self.assertRedirects(response, reverse("tasks:detail", args=[task.pk]))
        self.assertEqual(task.author, self.manager)
        self.assertEqual(task.assignee, self.bob)


class TaskDeleteTests(RolesDataMixin, TestCase):
    def test_employee_cannot_delete_even_own_task(self):
        self.login_as(self.alice)
        for task in (self.alice_task, self.bob_task):
            for method in ("get", "post"):
                with self.subTest(task=task.title, method=method):
                    response = getattr(self.client, method)(reverse("tasks:delete", args=[task.pk]))
                    self.assertEqual(response.status_code, 403)
        self.assertEqual(Task.objects.count(), 4)

    def test_manager_can_delete_task(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("tasks:delete", args=[self.bob_task.pk]))
        self.assertRedirects(response, reverse("tasks:list"))
        self.assertFalse(Task.objects.filter(pk=self.bob_task.pk).exists())


class TaskCommentTests(RolesDataMixin, TestCase):
    def _url(self, task):
        return reverse("tasks:add_comment", args=[task.pk])

    def test_employee_can_comment_on_visible_task(self):
        self.login_as(self.alice)
        response = self.client.post(self._url(self.alice_task), {"body": "Привет из теста"})
        self.assertRedirects(response, reverse("tasks:detail", args=[self.alice_task.pk]))
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.alice)
        self.assertEqual(comment.task, self.alice_task)

    def test_comment_author_and_task_cannot_be_forged(self):
        self.login_as(self.alice)
        self.client.post(self._url(self.alice_task),
                         {"body": "x", "author": self.bob.pk, "task": self.bob_task.pk})
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.alice)
        self.assertEqual(comment.task, self.alice_task)

    def test_employee_cannot_comment_on_foreign_task(self):
        self.login_as(self.alice)
        response = self.client.post(self._url(self.bob_task), {"body": "Чужая задача"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Comment.objects.count(), 0)

    def test_manager_can_comment_on_any_task(self):
        self.login_as(self.manager)
        self.client.post(self._url(self.alice_task), {"body": "От руководителя"})
        self.assertEqual(Comment.objects.get().author, self.manager)

    def test_anonymous_cannot_comment(self):
        response = self.client.post(self._url(self.alice_task), {"body": "аноним"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_get_is_not_allowed(self):
        self.login_as(self.alice)
        self.assertEqual(self.client.get(self._url(self.alice_task)).status_code, 405)

    def test_empty_comment_is_not_saved(self):
        self.login_as(self.alice)
        self.client.post(self._url(self.alice_task), {"body": ""})
        self.assertEqual(Comment.objects.count(), 0)

    def test_comments_are_shown_on_task_page(self):
        Comment.objects.create(task=self.alice_task, author=self.manager, body="Видимый комментарий")
        self.login_as(self.alice)
        response = self.client.get(reverse("tasks:detail", args=[self.alice_task.pk]))
        self.assertContains(response, "Видимый комментарий")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TaskFileUploadTests(RolesDataMixin, TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_employee_can_attach_file_to_new_task(self):
        self.login_as(self.alice)
        upload = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
        self.client.post(reverse("tasks:create"), {
            "title": "With file", "description": "", "priority": Task.Priority.MEDIUM.value,
            "project": self.project.pk, "deadline": "", "attachment": upload,
        })
        task = Task.objects.get(title="With file")
        self.assertTrue(task.attachment.name.startswith("tasks/"))
        with task.attachment.open("rb") as stored:
            self.assertEqual(stored.read(), b"hello")