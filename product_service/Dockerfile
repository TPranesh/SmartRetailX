# Product Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements from root build context
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY product_service /app/product_service

ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "product_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
