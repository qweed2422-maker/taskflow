#!/usr/bin/env python3
"""
scaffold_architecture.py
=========================

Генератор скелета проекта TaskFlow согласно ARCHITECTURE.md.

Что делает:
    1. Проверяет, что скрипт запущен из корня Django-проекта (рядом с manage.py).
    2. Создаёт Django-приложения accounts, projects, tasks, dashboard
       через "python manage.py startapp <name>" (если их ещё нет).
    3. Добавляет в каждое приложение файлы-заглушки, которых нет в стандартном
       startapp, но которые понадобятся по архитектуре (forms.py, urls.py,
       permissions.py, management-команда).
    4. Создаёт папку fixtures/ (для будущей db.json).
    5. Создаёт структуру templates/ (base.html, registration/login.html,
       папки под projects/tasks/dashboard) как пустые заготовки.

Чего НЕ делает (сознательно, чтобы не забегать вперёд по этапам):
    - НЕ добавляет приложения в INSTALLED_APPS в config/settings.py.
    - НЕ подключает urls.py приложений в config/urls.py.
    - НЕ пишет модели, views, формы, CRUD-логику.
    - НЕ трогает уже существующие файлы — только создаёт отсутствующие.

Запуск:
    (venv) $ python scaffold_architecture.py
    (venv) $ python scaffold_architecture.py --dry-run   # только показать план, ничего не создавать
"""

import argparse
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
MANAGE_PY = PROJECT_ROOT / "manage.py"

APPS = ["accounts", "projects", "tasks", "dashboard"]

STUB_URLS_PY = '''"""
URL-маршруты приложения "{app}".
Будут заполнены на соответствующем этапе реализации (CRUD / auth / dashboard).
"""
from django.urls import path

app_name = "{app}"

urlpatterns = [
    # TODO: добавить маршруты на профильном этапе
]
'''

STUB_FORMS_PY = '''"""
Django-формы приложения "{app}".
Будут заполнены на этапе реализации CRUD.
"""
from django import forms  # noqa: F401

# TODO: описать ModelForm-ы на профильном этапе
'''

STUB_PERMISSIONS_PY = '''"""
Миксины и хелперы для проверки ролей (Руководитель / Сотрудник).

Будут реализованы на этапе "Группы и права доступа".
Ключевой принцип (см. ARCHITECTURE.md, раздел 5):
любой view, отдающий конкретный объект, обязан дополнительно
ограничивать queryset по правам пользователя, а не только проверять роль
на уровне доступа к view.
"""

# TODO: ManagerRequiredMixin
# TODO: EmployeeOwnObjectMixin (фильтрация queryset по author/assignee)
'''

STUB_SEED_COMMAND = '''"""
Management-команда для генерации тестовых данных.

Использование (после реализации на этапе "Тестовая фикстура"):
    python manage.py seed_demo_data

Должна создать:
    - 1 руководителя;
    - 4 сотрудников;
    - 3-4 проекта;
    - 10-15 задач с разными статусами и приоритетами;
    - несколько комментариев.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создаёт демонстрационные данные для TaskFlow (заглушка)"

    def handle(self, *args, **options):
        # TODO: реализовать генерацию данных на профильном этапе
        self.stdout.write(
            self.style.WARNING(
                "Команда ещё не реализована. См. этап 'Тестовая фикстура'."
            )
        )
'''

STUB_BASE_HTML = """<!--
    base.html - базовый шаблон проекта (Bootstrap-каркас).
    Будет заполнен на этапе реализации CRUD/UI.
-->
"""

STUB_LOGIN_HTML = """<!--
    registration/login.html - форма входа.
    Будет заполнена на этапе "Аутентификация".
-->
"""

# Дополнительные файлы для каждого приложения: (относительный путь, содержимое)
EXTRA_APP_FILES = {
    "accounts": [
        ("permissions.py", STUB_PERMISSIONS_PY.format(app="accounts")),
        ("management/__init__.py", ""),
        ("management/commands/__init__.py", ""),
        ("management/commands/seed_demo_data.py", STUB_SEED_COMMAND),
    ],
    "projects": [
        ("forms.py", STUB_FORMS_PY.format(app="projects")),
        ("urls.py", STUB_URLS_PY.format(app="projects")),
    ],
    "tasks": [
        ("forms.py", STUB_FORMS_PY.format(app="tasks")),
        ("urls.py", STUB_URLS_PY.format(app="tasks")),
    ],
    "dashboard": [
        ("urls.py", STUB_URLS_PY.format(app="dashboard")),
    ],
}

# Папки templates/ с заглушками
TEMPLATE_FILES = {
    "templates/base.html": STUB_BASE_HTML,
    "templates/registration/login.html": STUB_LOGIN_HTML,
    "templates/projects/.gitkeep": "",
    "templates/tasks/.gitkeep": "",
    "templates/dashboard/.gitkeep": "",
}

FIXTURES_FILES = {
    "fixtures/.gitkeep": "",
}


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def log_create(path: Path) -> None:
    print(f"  [создано]  {path.relative_to(PROJECT_ROOT)}")


def log_skip(path: Path) -> None:
    print(f"  [пропущено, уже существует]  {path.relative_to(PROJECT_ROOT)}")


def write_file_if_absent(path: Path, content: str, dry_run: bool) -> None:
    if path.exists():
        log_skip(path)
        return
    if dry_run:
        print(f"  [будет создано]  {path.relative_to(PROJECT_ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log_create(path)


def create_app_if_absent(app_name: str, dry_run: bool) -> None:
    app_dir = PROJECT_ROOT / app_name
    if app_dir.exists():
        log_skip(app_dir)
        return
    if dry_run:
        print(f"  [будет выполнено]  python manage.py startapp {app_name}")
        return
    print(f"  -> python manage.py startapp {app_name}")
    result = subprocess.run(
        [sys.executable, str(MANAGE_PY), "startapp", app_name],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print(f"  ОШИБКА: не удалось создать приложение {app_name}")
        sys.exit(result.returncode)
    log_create(app_dir)


# ---------------------------------------------------------------------------
# Основной сценарий
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать, что будет создано, без реальных изменений",
    )
    args = parser.parse_args()

    if not MANAGE_PY.exists():
        print(
            "ОШИБКА: manage.py не найден рядом со скриптом.\n"
            "Поместите scaffold_architecture.py в корень проекта TaskFlow "
            "(туда же, где лежит manage.py) и запустите снова."
        )
        sys.exit(1)

    mode = "ПРОБНЫЙ ЗАПУСК (ничего не изменится)" if args.dry_run else "РЕАЛЬНОЕ СОЗДАНИЕ ФАЙЛОВ"
    print(f"=== Генерация скелета архитектуры TaskFlow — {mode} ===\n")

    # 1. Django-приложения
    print("1. Django-приложения:")
    for app in APPS:
        create_app_if_absent(app, args.dry_run)
    print()

    # 2. Дополнительные файлы-заглушки внутри приложений
    print("2. Дополнительные файлы приложений:")
    for app, files in EXTRA_APP_FILES.items():
        for rel_path, content in files:
            write_file_if_absent(PROJECT_ROOT / app / rel_path, content, args.dry_run)
    print()

    # 3. Папка fixtures/
    print("3. Папка fixtures/:")
    for rel_path, content in FIXTURES_FILES.items():
        write_file_if_absent(PROJECT_ROOT / rel_path, content, args.dry_run)
    print()

    # 4. Структура templates/
    print("4. Структура templates/:")
    for rel_path, content in TEMPLATE_FILES.items():
        write_file_if_absent(PROJECT_ROOT / rel_path, content, args.dry_run)
    print()

    print("=== Готово ===")
    print(
        "Напоминание: приложения ещё НЕ добавлены в INSTALLED_APPS "
        "и НЕ подключены в config/urls.py — это будет сделано на этапе моделей "
        "и последующих этапах, согласно согласованному порядку работы."
    )


if __name__ == "__main__":
    main()