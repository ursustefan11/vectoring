FROM python:3.11.6-slim

ENV BLENDER_VERSION=4.1.0 \
    BLENDER_URL=https://mirror.clarkson.edu/blender/release/Blender4.1/blender-4.1.0-linux-x64.tar.xz
    
WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    wget \
    xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O blender.tar.xz "${BLENDER_URL}" && \
    tar -xJf blender.tar.xz -C /usr/local --strip-components=1 && \
    rm blender.tar.xz

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN find /usr/local -name blender -type f

ENV PATH="/usr/local:${PATH}"

RUN blender --version

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "600", "app:app"]