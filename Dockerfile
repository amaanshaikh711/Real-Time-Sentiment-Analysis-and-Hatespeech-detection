# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# build-essential and gcc might be needed for some python packages like numpy/scipy if wheels aren't available
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
# We upgrade pip to the latest version first
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Download NLTK data (stopwords)
RUN python -m nltk.downloader stopwords

# Copy the rest of the application code
COPY . /app/

# Expose the port that the app runs on
EXPOSE 10000

# Define the command to run the application using Gunicorn
# app:app refers to the 'app' object in 'app.py'
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "120", "app:app"]
