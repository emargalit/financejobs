from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.JobListAPIView.as_view(), name='job-list'),
    path('jobs/filters/', views.JobFiltersView.as_view(), name='job-filters'),
    path('jobs/<int:pk>/', views.JobRetrieveAPIView.as_view(), name='job-retrieve'),
    path('companies/', views.CompanyListAPIView.as_view(), name='company-list'),
    path('checkout/config/', views.CheckoutConfigView.as_view()),
    path('invoice-requests/', views.InvoiceRequestView.as_view()),
    path('checkout/', views.CheckoutView.as_view()),
    path('checkout/status/', views.PaymentStatusView.as_view()),
    path('stripe/webhook/', views.StripeWebhookView.as_view()),
    path('newsletter/subscribe/', views.NewsletterSubscribeView.as_view()),
    path('newsletter/confirm/', views.NewsletterConfirmView.as_view()),
    path('newsletter/unsubscribe/', views.NewsletterUnsubscribeView.as_view()),
    path('health/', views.HealthView.as_view()),
]
