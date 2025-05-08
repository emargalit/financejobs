from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Job, Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_type')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type')
    list_filter = ('job_type', 'location', 'company')
    search_fields = ('title', 'description')
