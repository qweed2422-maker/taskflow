from django import forms

from .models import Task


class BaseTaskForm(forms.ModelForm):
    """Общая настройка виджетов и querysets для всех форм задачи."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "assignee" in self.fields:
            self.fields["assignee"].queryset = self.fields["assignee"].queryset.filter(is_active=True)
            self.fields["assignee"].required = False

    class Meta:
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "attachment": forms.FileInput(),
        }


class ManagerTaskForm(BaseTaskForm):
    """Полная форма — доступна только руководителю."""

    class Meta(BaseTaskForm.Meta):
        model = Task
        fields = ["title", "description", "status", "priority", "assignee", "project", "deadline", "attachment"]


class EmployeeCreateTaskForm(BaseTaskForm):
    """
    Сотрудник создаёт задачу и автоматически становится её автором
    (author проставляется во view, не в форме). Назначение исполнителя —
    право руководителя, поэтому поля assignee здесь нет.
    """

    class Meta(BaseTaskForm.Meta):
        model = Task
        fields = ["title", "description", "priority", "project", "deadline", "attachment"]


class EmployeeEditTaskForm(BaseTaskForm):
    """
    Сотрудник редактирует только свою задачу (автор/исполнитель).
    Может менять статус, но не исполнителя и не проект.
    """

    class Meta(BaseTaskForm.Meta):
        model = Task
        fields = ["title", "description", "status", "priority", "deadline", "attachment"]

from .models import Comment


class CommentForm(forms.ModelForm):
    """
    Форма комментария содержит только текст. Автор и задача
    проставляются во view (request.user и task из URL), чтобы
    их нельзя было подделать через отправку произвольных данных формы.
    """

    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Ваш комментарий..."}),
        }
        labels = {
            "body": "",
        }