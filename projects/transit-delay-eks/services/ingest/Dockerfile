FROM python:3.11-slim

WORKDIR /app

COPY projects/transit-delay-eks/services/ingest/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY projects/transit-delay-eks/services/ingest/consumer.py .

CMD ["sh", "-c", "python consumer.py --kinesis-stream ${KINESIS_STREAM:-} --s3-bucket ${RAW_BUCKET:-} --kinesis-limit 200"]
