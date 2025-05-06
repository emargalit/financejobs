from django.db import models

class Job(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255, blank=True, null=True)
    apply_link = models.URLField(max_length=500)
    posted_at = models.DateTimeField(auto_now_add=True)
    job_type = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('title', 'company_name', 'location') 

    def __str__(self):
        return self.title