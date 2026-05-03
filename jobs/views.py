from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from .models import Job, Company, NewsletterSubscriber
from .serializers import JobSerializer, JobInquirySerializer, CompanySerializer, NewsletterSubscriberSerializer
from rest_framework import viewsets
from rest_framework.generics import ListAPIView


class NewsletterSubscribeView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NewsletterSubscriberSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Successfully subscribed."},
                status=status.HTTP_201_CREATED,
            )

        if "email" in serializer.errors:
            return Response(
                {"detail": "This email is already subscribed or invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyListAPIView(ListAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

class JobListCreateAPIView(generics.ListCreateAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer

class JobRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class JobInquiryView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = JobInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        subject = f"New job advertisement request: {data['title']}"
        message = (
            f"A new job advertisement request was submitted.\n\n"
            f"Company: {data['company_name']}\n"
            f"Ordering person email: {data['contact_email']}\n"
            f"Job title: {data['title']}\n"
            f"Location: {data['location']}\n"
            f"Salary: {data.get('salary', '')}\n"
            f"Apply link: {data['apply_link']}\n\n"
            f"Description:\n{data['description']}\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["elene.margalit@gmail.com"],
            fail_silently=False,
        )

        return Response(
            {"detail": "Job advertisement request sent successfully."},
            status=status.HTTP_200_OK,
        )