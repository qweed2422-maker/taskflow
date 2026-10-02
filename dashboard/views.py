from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from tasks.models import Task


@login_required
def dashboard_home(request):
    visible_tasks = Task.objects.visible_to(request.user)

    status_stats = [
        {"label": label, "count": visible_tasks.filter(status=value).count()}
        for value, label in Task.Status.choices
    ]

    priority_stats = [
        {"label": label, "count": visible_tasks.filter(priority=value).count()}
        for value, label in Task.Priority.choices
    ]

    overdue_count = (
        visible_tasks
        .filter(deadline__lt=timezone.localdate())
        .exclude(status=Task.Status.DONE)
        .count()
    )

    context = {
        "total_tasks": visible_tasks.count(),
        "status_stats": status_stats,
        "priority_stats": priority_stats,
        "overdue_count": overdue_count,
    }
    return render(request, "dashboard/home.html", context)