"""
Миксины и хелперы для проверки ролей (Руководитель / Сотрудник).

Ключевой принцип (см. ARCHITECTURE.md, раздел 5): эти инструменты
проверяют ТОЛЬКО доступ к самому view. Они не заменяют фильтрацию
queryset внутри view — фильтрация обязательна на каждом view, который
отдаёт конкретный объект по pk, иначе сотрудник сможет получить чужую
задачу простой подменой ID в URL.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

MANAGERS_GROUP = "Managers"
EMPLOYEES_GROUP = "Employees"


def is_manager(user) -> bool:
    """Руководитель: суперпользователь либо состоит в группе Managers."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=MANAGERS_GROUP).exists()


def is_employee(user) -> bool:
    """Сотрудник: аутентифицирован и не является руководителем."""
    return user.is_authenticated and not is_manager(user)


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Доступ к view только для Руководителя.
    Аноним перенаправляется на страницу входа, вошедший сотрудник получает 403.
    """

    def test_func(self):
        return is_manager(self.request.user)


class EmployeeOrManagerMixin(LoginRequiredMixin):
    """
    Базовый миксин для view, доступных обеим ролям при условии входа
    в систему. Ограничение "видит только свои задачи" реализуется
    в get_queryset() конкретного view (этап 8), а не здесь.
    """
    pass