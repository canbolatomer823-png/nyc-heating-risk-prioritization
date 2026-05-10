FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Use JSON format for environment variables if possible, but defaults are in code
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
