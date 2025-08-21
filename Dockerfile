# Start with an official, lightweight Python 3.11 image.
FROM python:3.11-slim

# Set the working directory inside the container to /app.
WORKDIR /app

# Copy ONLY the requirements file first. Docker is smart and will cache this layer.
# If you don't change your requirements, this step won't re-run, making future builds faster.
COPY requirements.txt .

# Install all the Python dependencies from the requirements file.
RUN pip install --no-cache-dir -r requirements.txt

COPY test_challenge.py .

# Now, copy your application code into the /app directory inside the container.
COPY ./app /app/app

# Tell Docker that the application inside the container will be listening on port 8000.
EXPOSE 8000

# The command to execute when the container starts.
# This runs your FastAPI server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]