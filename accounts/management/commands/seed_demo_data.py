"""
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
