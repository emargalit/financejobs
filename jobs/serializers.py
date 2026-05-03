from rest_framework import serializers
from .models import Company, Job, NewsletterSubscriber


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["id", "email", "created_at"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'company_type', 'logo']


class JobInquirySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    company_name = serializers.CharField(max_length=255)
    contact_email = serializers.EmailField()
    location = serializers.CharField(max_length=255)
    salary = serializers.CharField(max_length=255, required=False, allow_blank=True)
    apply_link = serializers.URLField()


class JobSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source='company',
        write_only=True
    )

    class Meta:
        model = Job
        fields = '__all__'



