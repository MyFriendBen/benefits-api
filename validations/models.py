from screener.models import Screen
from django.db import models


class Validation(models.Model):
    screen = models.ForeignKey(Screen, related_name="validations", on_delete=models.CASCADE)
    program_name = models.CharField(max_length=120)
    eligible = models.BooleanField()
    value = models.DecimalField(decimal_places=2, max_digits=10)
    notes = models.TextField(blank=True, default="")
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("screen", "program_name")

    @property
    def screen_uuid(self):
        return self.screen.uuid

    @screen_uuid.setter
    def screen_uuid(self, value):
        self.screen = Screen.objects.get(uuid=value)
