from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

from accounts.permissions import ManagerRequiredMixin
from .models import Project


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 10


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"


class ProjectCreateView(ManagerRequiredMixin, CreateView):
    model = Project
    fields = ["title", "description"]
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:list")


class ProjectUpdateView(ManagerRequiredMixin, UpdateView):
    model = Project
    fields = ["title", "description"]
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:list")


class ProjectDeleteView(ManagerRequiredMixin, DeleteView):
    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("projects:list")