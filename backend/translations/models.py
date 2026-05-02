from django.db import models

class TranslationHistory(models.Model):
    user_email = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_email}: {self.text}"
