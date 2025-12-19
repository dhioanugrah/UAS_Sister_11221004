FROM python:3.11-slim

RUN useradd -m appuser
WORKDIR /app

ARG INSTALL_DEV=0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# install dev deps kalau INSTALL_DEV=1
COPY requirements-dev.txt ./requirements-dev.txt
RUN if [ "$INSTALL_DEV" = "1" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY app ./app
COPY ../tests /tests/  

USER appuser
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
