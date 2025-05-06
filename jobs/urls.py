from django.urls import path
from .views import JobListCreateAPIView, JobRetrieveAPIView

urlpatterns = [
    path('jobs/', JobListCreateAPIView.as_view(), name='job-list-create'),
    path('jobs/<int:pk>/', JobRetrieveAPIView.as_view(), name='job-retrieve'),
]