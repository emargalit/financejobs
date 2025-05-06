from django.core.management.base import BaseCommand
from jobs.models import Job
from asgiref.sync import sync_to_async
import asyncio

async def delete_all_jobs():
    jobs = await sync_to_async(list)(Job.objects.all())
    print(f"Deleting {len(jobs)} jobs...")
    for job in jobs:
        print(f"🗑️ Deleting: {job.title}")
        await sync_to_async(job.delete)()

class Command(BaseCommand):
    help = 'Delete all saved jobs'

    def handle(self, *args, **kwargs):
        print("Starting job deletion...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(delete_all_jobs())
