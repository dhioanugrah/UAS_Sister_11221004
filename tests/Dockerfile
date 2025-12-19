FROM python:3.11-slim

WORKDIR /tests

RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    requests

COPY tests ./tests

CMD ["pytest", "-v"]
