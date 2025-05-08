from django.urls import path
from .views import JobListCreateAPIView, JobRetrieveAPIView, CompanyListAPIView

urlpatterns = [
    path('jobs/', JobListCreateAPIView.as_view(), name='job-list-create'),
    path('jobs/<int:pk>/', JobRetrieveAPIView.as_view(), name='job-retrieve'),
    path('companies/', CompanyListAPIView.as_view(), name='company-list'),
]