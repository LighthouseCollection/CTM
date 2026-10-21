FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        libglib2.0-0 \
        shared-mime-info \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 ctm && useradd -u 1000 -g ctm -m ctm

WORKDIR /app

COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py /app/manage.py
COPY ctm /app/ctm
COPY tribunal /app/tribunal
COPY static /app/static

RUN DJANGO_DEBUG=true DJANGO_SECRET_KEY=build-time-static-only-not-runtime python manage.py collectstatic --noinput

EXPOSE 8000

USER ctm

CMD ["gunicorn", "ctm.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]
