from .permissions import is_manager as _is_manager


def role_flags(request):
    """
    Добавляет is_manager/is_employee в контекст каждого шаблона,
    чтобы можно было показывать/скрывать кнопки управления по роли.
    Это влияет только на отображение интерфейса — реальная защита
    от доступа обеспечивается миксинами и фильтрацией queryset в views.
    """
    user = request.user
    return {
        "is_manager": _is_manager(user) if user.is_authenticated else False,
    }