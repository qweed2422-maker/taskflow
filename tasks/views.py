from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from accounts.permissions import ManagerRequiredMixin, is_manager
from .forms import ManagerTaskForm, EmployeeCreateTaskForm, EmployeeEditTaskForm
from .models import Task
from django.contrib.auth.models import User

from projects.models import Project

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View

from .forms import ManagerTaskForm, EmployeeCreateTaskForm, EmployeeEditTaskForm, CommentForm

class VisibleTasksMixin:
    """
    Ограничивает queryset по правам пользователя — см. Task.objects.visible_to().

    Это единая точка защиты от доступа к чужой задаче через подмену id
    в URL: если задача не входит в этот queryset, Django на любом view
    (detail/edit) вернёт 404, а не отдаст данные и не покажет форму.
    """

    def get_base_queryset(self):
        return Task.objects.select_related("project", "author", "assignee").visible_to(self.request.user)


class TaskListView(LoginRequiredMixin, VisibleTasksMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 10

    def get_queryset(self):
        qs = self.get_base_queryset()

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(title__icontains=query)

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        assignee_id = self.request.GET.get("assignee", "").strip()
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)

        project_id = self.request.GET.get("project", "").strip()
        if project_id:
            qs = qs.filter(project_id=project_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Выпадающие списки для фильтров строим на основе queryset,
        # видимого пользователю по правам доступа (без учёта поиска/
        # других фильтров) — так сотрудник не увидит в списке исполнителей
        # или проектов то, что не относится к его задачам.
        visible = self.get_base_queryset()

        context["status_choices"] = Task.Status.choices
        context["assignees"] = (
            User.objects.filter(assigned_tasks__in=visible)
            .distinct()
            .order_by("username")
        )
        context["projects"] = (
            Project.objects.filter(tasks__in=visible)
            .distinct()
            .order_by("title")
        )

        # Текущие значения фильтров — чтобы форма оставалась заполненной
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_assignee"] = self.request.GET.get("assignee", "")
        context["current_project"] = self.request.GET.get("project", "")

        return context


class TaskDetailView(LoginRequiredMixin, VisibleTasksMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return self.get_base_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentForm()
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    template_name = "tasks/task_form.html"

    def get_form_class(self):
        return ManagerTaskForm if is_manager(self.request.user) else EmployeeCreateTaskForm

    def form_valid(self, form):
        # Автор задачи — всегда тот, кто её создал, независимо от роли.
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tasks:detail", kwargs={"pk": self.object.pk})


class TaskUpdateView(LoginRequiredMixin, VisibleTasksMixin, UpdateView):
    model = Task
    template_name = "tasks/task_form.html"

    def get_queryset(self):
        # Тот же queryset, что и для просмотра: сотрудник может
        # редактировать ровно те задачи, которые ему видны (свои),
        # а не любые задачи в проекте.
        return self.get_base_queryset()

    def get_form_class(self):
        return ManagerTaskForm if is_manager(self.request.user) else EmployeeEditTaskForm

    def get_success_url(self):
        return reverse_lazy("tasks:detail", kwargs={"pk": self.object.pk})


class TaskDeleteView(ManagerRequiredMixin, DeleteView):
    """Удаление задачи — только руководитель, у сотрудника такого права нет."""
    model = Task
    template_name = "tasks/task_confirm_delete.html"
    success_url = reverse_lazy("tasks:list")

class CommentCreateView(LoginRequiredMixin, VisibleTasksMixin, View):
    """
    Добавление комментария к задаче. Доступно любому пользователю,
    которому сама задача видна по правам (руководителю — к любой,
    сотруднику — к своим, см. VisibleTasksMixin). Если подставить в URL
    id невидимой задачи, get_object_or_404 вернёт 404 — та же защита,
    что и на detail/edit (этап 8).
    """

    def post(self, request, pk):
        task = get_object_or_404(self.get_base_queryset(), pk=pk)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
        else:
            messages.error(request, "Не удалось добавить комментарий — проверьте текст.")
        return redirect("tasks:detail", pk=task.pk)