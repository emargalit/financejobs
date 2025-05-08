from rest_framework import generics
from .models import Job
from .models import Company
from .serializers import JobSerializer
from rest_framework import viewsets
from .serializers import CompanySerializer
from rest_framework.generics import ListAPIView


class CompanyListAPIView(ListAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

class JobListCreateAPIView(generics.ListCreateAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer

class JobRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer