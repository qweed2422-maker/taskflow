import random
from datetime import timedelta

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.permissions import MANAGERS_GROUP, EMPLOYEES_GROUP
from projects.models import Project
from tasks.models import Task, Comment

MANAGER_USERNAME = "manager"
MANAGER_PASSWORD = "Manager2026!"

EMPLOYEE_USERNAMES = ["employee1", "employee2", "employee3", "employee4"]
EMPLOYEE_DEFAULT_PASSWORD = "Employee2026!"

PROJECTS_DATA = [
    ("Редизайн корпоративного сайта", "Обновление дизайна и вёрстки основного сайта компании."),
    ("Внутренняя CRM-система", "Разработка системы учёта клиентов для отдела продаж."),
    ("Мобильное приложение поддержки", "Приложение для обращений клиентов в техподдержку."),
    ("Автоматизация тестирования", "Покрытие ключевых пользовательских сценариев автотестами."),
]


class Command(BaseCommand):
    help = "Создаёт демонстрационные данные для TaskFlow (пользователи, проекты, задачи, комментарии)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить существующие Project/Task/Comment перед генерацией "
                 "(пользователи и группы не затрагиваются).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["reset"] and Project.objects.exists():
            self.stdout.write(self.style.WARNING(
                "В базе уже есть проекты. Запустите команду с флагом --reset, "
                "чтобы пересоздать демо-данные (Project/Task/Comment будут "
                "удалены и созданы заново; пользователи и группы останутся)."
            ))
            return

        if options["reset"]:
            Comment.objects.all().delete()
            Task.objects.all().delete()
            Project.objects.all().delete()
            self.stdout.write("Старые Project/Task/Comment удалены.")

        managers_group, _ = Group.objects.get_or_create(name=MANAGERS_GROUP)
        employees_group, _ = Group.objects.get_or_create(name=EMPLOYEES_GROUP)

        manager = self._get_or_create_user(
            MANAGER_USERNAME, MANAGER_PASSWORD,
            is_staff=True, is_superuser=True,
        )
        manager.groups.add(managers_group)

        employees = []
        for username in EMPLOYEE_USERNAMES:
            employee = self._get_or_create_user(
                username, EMPLOYEE_DEFAULT_PASSWORD,
                is_staff=False, is_superuser=False,
            )
            employee.groups.add(employees_group)
            employees.append(employee)

        projects = [
            Project.objects.create(title=title, description=description)
            for title, description in PROJECTS_DATA
        ]

        tasks = self._create_tasks(manager, employees, projects)
        self._create_comments(manager, employees, tasks)

        self.stdout.write(self.style.SUCCESS(
            f"Готово: 1 руководитель, {len(employees)} сотрудника(ов), "
            f"{len(projects)} проекта(ов), {len(tasks)} задач(и)."
        ))
        self.stdout.write(
            f"Логины: {MANAGER_USERNAME}/{MANAGER_PASSWORD} (руководитель), "
            f"{', '.join(EMPLOYEE_USERNAMES)} — новые пароли "
            f"'{EMPLOYEE_DEFAULT_PASSWORD}' (у уже существовавших пользователей "
            f"пароль не менялся)."
        )

    @staticmethod
    def _get_or_create_user(username, password, *, is_staff, is_superuser):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": is_staff, "is_superuser": is_superuser, "is_active": True},
        )
        if created:
            user.set_password(password)
            user.save()
        else:
            # Пользователь уже существовал (например, создан вручную раньше) —
            # пароль не трогаем, только гарантируем нужные флаги доступа.
            changed = False
            if user.is_staff != is_staff:
                user.is_staff = is_staff
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                user.save()
        return user

    @staticmethod
    def _create_tasks(manager, employees, projects):
        today = timezone.localdate()
        e1, e2, e3, e4 = employees

        # (title, description, project_idx, author, assignee, status, priority, deadline_offset_days)
        plan = [
            ("Сделать макет главной страницы", "Подготовить макет в Figma.", 0, manager, e1, Task.Status.DONE, Task.Priority.MEDIUM, -10),
            ("Вёрстка адаптивных блоков", "Адаптировать вёрстку под мобильные экраны.", 0, e1, e1, Task.Status.IN_PROGRESS, Task.Priority.HIGH, 5),
            ("Подключить аналитику", "Настроить сбор метрик посещаемости.", 0, manager, e2, Task.Status.NEW, Task.Priority.LOW, 14),
            ("Спроектировать схему БД CRM", "Продумать таблицы и связи.", 1, manager, e2, Task.Status.DONE, Task.Priority.HIGH, -20),
            ("Реализовать карточку клиента", "Форма просмотра и редактирования клиента.", 1, e2, e2, Task.Status.IN_PROGRESS, Task.Priority.HIGH, -2),
            ("Добавить фильтры в список клиентов", "Фильтрация по статусу и менеджеру.", 1, manager, e3, Task.Status.NEW, Task.Priority.MEDIUM, 7),
            ("Настроить права доступа в CRM", "Роли: менеджер, администратор.", 1, manager, None, Task.Status.NEW, Task.Priority.HIGH, 3),
            ("Прототип экрана обращений", "Экран списка и деталей обращения.", 2, e3, e3, Task.Status.IN_PROGRESS, Task.Priority.MEDIUM, 10),
            ("Push-уведомления", "Настроить push при смене статуса обращения.", 2, manager, e4, Task.Status.NEW, Task.Priority.LOW, -5),
            ("Интеграция с API поддержки", "Подключение к внешнему сервису тикетов.", 2, e4, e4, Task.Status.DONE, Task.Priority.MEDIUM, -15),
            ("Написать автотесты для входа", "Покрыть сценарии логина/логаута.", 3, manager, e1, Task.Status.IN_PROGRESS, Task.Priority.HIGH, 2),
            ("Настроить CI для прогона тестов", "GitHub Actions на каждый push.", 3, manager, e4, Task.Status.NEW, Task.Priority.MEDIUM, 20),
            ("Покрыть тестами CRUD задач", "Тесты на создание/редактирование/удаление.", 3, e1, e1, Task.Status.NEW, Task.Priority.HIGH, -1),
            ("Ревью тестового покрытия", "Проверить процент покрытия кода.", 3, manager, e3, Task.Status.DONE, Task.Priority.LOW, -30),
        ]

        tasks = []
        for title, description, project_idx, author, assignee, status, priority, offset in plan:
            tasks.append(Task.objects.create(
                title=title,
                description=description,
                project=projects[project_idx],
                author=author,
                assignee=assignee,
                status=status,
                priority=priority,
                deadline=today + timedelta(days=offset),
            ))
        return tasks

    @staticmethod
    def _create_comments(manager, employees, tasks):
        commenters = [manager, *employees]
        sample_texts = [
            "Приступил к работе, дам знать по ходу.",
            "Нужно уточнить требования у заказчика.",
            "Готово, можно проверять.",
            "Возникла небольшая задержка, перенесу на пару дней.",
        ]
        # Добавляем по 1-2 комментария к части задач для наглядности.
        for task in tasks[:8]:
            for _ in range(random.randint(1, 2)):
                Comment.objects.create(
                    task=task,
                    author=random.choice(commenters),
                    body=random.choice(sample_texts),
                )