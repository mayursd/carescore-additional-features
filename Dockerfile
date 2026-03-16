# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Set the PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the Streamlit application
# Use the full path to app.py inside the src directory
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]