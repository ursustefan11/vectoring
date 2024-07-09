FROM blender:latest

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    libopencv-dev \
    python3-opencv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt /workspace/
RUN pip3 install --no-cache-dir -r /workspace/requirements.txt

# Copy the Python script into the container
COPY your_script.py /workspace/

# Create output directory
RUN mkdir -p /workspace/output

# Set the working directory
WORKDIR /workspace/

# Define the entry point for the container
ENTRYPOINT ["blender", "--background", "--python", "your_script.py", "--"]
