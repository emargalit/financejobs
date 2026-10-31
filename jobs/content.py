import bleach

JOB_TYPES = ('Permanent', 'Internships / Graduate Programs', 'Fixed-Term / Contract', 'Part-Time')

def clean_description(value):
    return bleach.clean(value or '', tags=['p', 'br', 'div', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'a', 'blockquote'], attributes={'a': ['href', 'title']}, protocols=['https', 'http', 'mailto'], strip=True)

def normalize_job_type(value):
    translations = {'Festanstellung': 'Permanent', 'Praktika & Trainee-Stellen': 'Internships / Graduate Programs', 'Befristet': 'Fixed-Term / Contract', 'Teilzeit': 'Part-Time'}
    value = translations.get(value, value)
    return value if value in JOB_TYPES else ''
