FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python modules and configuration
COPY lineage.py /app/
COPY config.py /app/
COPY session_state.py /app/
COPY path_utils.py /app/
COPY file_watcher.py /app/
COPY instruction_files.py /app/
COPY appsettings.json /app/

# Copy the tools package
COPY tools/ /app/tools/

# Create a directory to mount the local files
RUN mkdir /data

# Command to run the server
CMD ["python", "lineage.py"]
