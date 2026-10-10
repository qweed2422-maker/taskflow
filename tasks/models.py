from django.conf import settings
from django.db import models
import os

from projects.models import Project

class TaskQuerySet(models.QuerySet):
    def visible_to(self, user):
        """
        Задачи, видимые пользователю по правам доступа.
        Руководитель видит все задачи, сотрудник — только те,
        где он автор или исполнитель. Используется и в CRUD задач,
        и в дашборде, чтобы логика видимости не дублировалась.
        """
        from accounts.permissions import is_manager  # локальный импорт — без циклической зависимости

        if is_manager(user):
            return self
        return self.filter(models.Q(author=user) | models.Q(assignee=user))

class Task(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        DONE = "done", "Готово"

    class Priority(models.TextChoices):
        HIGH = "high", "Высокий"
        MEDIUM = "medium", "Средний"
        LOW = "low", "Низкий"

    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True)

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    priority = models.CharField(
        "Приоритет",
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    objects = TaskQuerySet.as_manager()

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        related_name="authored_tasks",
        on_delete=models.CASCADE,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Исполнитель",
        related_name="assigned_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Проект",
        related_name="tasks",
        on_delete=models.CASCADE,
    )

    deadline = models.DateField("Дедлайн", null=True, blank=True)
    attachment = models.FileField(
        "Файл",
        upload_to="tasks/%Y/%m/",
        null=True,
        blank=True,
    )
    @property
    def attachment_filename(self):
        return os.path.basename(self.attachment.name) if self.attachment else ""

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-id"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    task = models.ForeignKey(
        Task,
        verbose_name="Задача",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    body = models.TextField("Текст")
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"Комментарий {self.author} к задаче «{self.task}»"
