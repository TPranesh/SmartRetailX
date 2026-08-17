# Inventory Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements from root build context
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY inventory_service /app/inventory_service

ENV PYTHONPATH=/app

EXPOSE 8004

CMD ["uvicorn", "inventory_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
