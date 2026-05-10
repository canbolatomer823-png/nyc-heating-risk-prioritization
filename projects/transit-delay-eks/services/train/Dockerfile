FROM python:3.11-slim

WORKDIR /app

COPY projects/transit-delay-eks/services/train/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY projects/transit-delay-eks/services/train/train.py .
COPY projects/transit-delay-eks/data/sample_bus_events.json data/sample_bus_events.json

CMD ["python", "train.py", "--input", "/app/data/sample_bus_events.json", "--output-dir", "/tmp/models"]
