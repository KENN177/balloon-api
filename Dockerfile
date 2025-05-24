# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy everything
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8080

# Run FastAPI app
CMD ["uvicorn", "drop_server:app", "--host", "0.0.0.0", "--port", "8080"]
