from django.db import models


class Project(models.Model):
    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ["title"]

    def __str__(self):
        return self.title