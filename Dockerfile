# Image pour le mode web (serveur). Voir README.md, section « Mode web ».
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CACAO_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt requirements-serveur.txt ./
RUN pip install --no-cache-dir -r requirements-serveur.txt
COPY . .
RUN python manage.py collectstatic --noinput
VOLUME /data
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py init_coop && gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3"]
