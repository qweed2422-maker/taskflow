from django.contrib import admin

from .models import Task, Comment


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("author", "created_at")
    fields = ("author", "body", "created_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "project",
        "status",
        "priority",
        "author",
        "assignee",
        "deadline",
    )
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")
    autocomplete_fields = ("author", "assignee", "project")
    inlines = [CommentInline]

    def save_formset(self, request, form, formset, change):
        """
        Comment.author не редактируется в инлайне (readonly), поэтому
        при создании нового комментария из админки автором автоматически
        становится текущий залогиненный пользователь.
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Comment) and not instance.author_id:
                instance.author = request.user
            instance.save()
        formset.save_m2m()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body",)