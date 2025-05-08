from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    company_type = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255, blank=True, null=True)
    apply_link = models.URLField(max_length=500)
    posted_at = models.DateTimeField(auto_now_add=True)
    job_type = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('title', 'company', 'location') 

    def __str__(self):
        return self.title