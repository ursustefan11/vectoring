FROM python:3.11.6-slim

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

ENV BLENDER_VERSION=4.1.0 \
    BLENDER_URL=https://mirror.clarkson.edu/blender/release/Blender4.1/blender-4.1.0-linux-x64.tar.xz

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    wget \
    xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN wget -O blender.tar.xz "${BLENDER_URL}"

RUN tar -xJf blender.tar.xz -C /usr/local --strip-components=1 \
    && rm blender.tar.xz

# Find the Blender executable to add its directory to PATH
RUN find /usr/local -name blender -type f

# Assuming the blender executable is in /usr/local/bin, adjust the PATH
ENV PATH="/usr/local:${PATH}"

# Verify the Blender installation
RUN blender --version

COPY . /workspace/

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
