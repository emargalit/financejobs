from rest_framework import serializers
from .models import Company, Job
from .content import clean_description, JOB_TYPES


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'company_type', 'logo']


class JobInquirySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=20000)
    company_name = serializers.CharField(max_length=255)
    contact_email = serializers.EmailField()
    location = serializers.CharField(max_length=255)
    salary = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    apply_link = serializers.URLField(max_length=500)
    job_type = serializers.ChoiceField(choices=JOB_TYPES, required=False, allow_blank=True, default='')
    request_id = serializers.UUIDField()

    def validate_apply_link(self, value):
        if not value.startswith(('https://', 'http://')):
            raise serializers.ValidationError('Use an http or https application link.')
        return value


class JobListSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Job
        fields = ['id', 'title', 'company', 'location', 'salary', 'posted_at', 'job_type', 'expires_at', 'source', 'source_posted_at', 'last_seen_at', 'work_schedule']


class JobSerializer(JobListSerializer):
    description = serializers.SerializerMethodField()

    def get_description(self, obj):
        # Also protects legacy records and imports that bypass model.save().
        return clean_description(obj.description)

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ['description', 'apply_link', 'source_url']
