FROM python:3.11-slim

WORKDIR /app

COPY projects/transit-delay-eks/services/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY projects/transit-delay-eks/services/api/main.py .
COPY projects/transit-delay-eks/data/sample_bus_events.json data/sample_bus_events.json

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000"]
