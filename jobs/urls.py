from django.urls import path
from .views import JobListCreateAPIView, JobRetrieveAPIView, CompanyListAPIView, JobInquiryView, NewsletterSubscribeView

urlpatterns = [
    path('jobs/', JobListCreateAPIView.as_view(), name='job-list-create'),
    path('jobs/<int:pk>/', JobRetrieveAPIView.as_view(), name='job-retrieve'),
    path('companies/', CompanyListAPIView.as_view(), name='company-list'),
    path('job-inquiries/', JobInquiryView.as_view(), name='job-inquiries'),
    path("newsletter/subscribe/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]