from rest_framework import generics
from .models import Job
from .serializers import JobSerializer

class JobListCreateAPIView(generics.ListCreateAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer

class JobRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer