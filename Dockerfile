FROM python:3.10

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of your application
COPY . .

# Set the default command to run main.py
CMD ["python", "main.py"]
