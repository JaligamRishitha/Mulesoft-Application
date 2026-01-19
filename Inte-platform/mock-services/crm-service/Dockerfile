FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY app.py .
COPY templates/ templates/
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8092"]
