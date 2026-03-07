
# Pipeline 3D: PDAL CLI → PyMeshLab → Instant Meshes
#
# PDAL: usado via CLI (pdal pipeline) — sem binding Python,
#       sem problema de compilação, com LAZ nativo via PPA.
# PyMeshLab: venv Python limpo, sem conflito de libs.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo

# 1. Base + libs de sistema
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget unzip \
    python3 python3-pip python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libopengl0 \
    xvfb \
    libxrandr2 libxinerama1 libxcursor1 libxi6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. PDAL via PPA ubuntugis — CLI com suporte a LAZ nativo
RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y \
    && apt-get update \
    && apt-get install -y pdal \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && pdal --version

# 3. PyMeshLab em venv isolado
#    venv garante que as libs do pymeshlab (manylinux wheel)
#    não conflitem com nada do sistema.
RUN python3 -m venv /opt/venv-mesh \
    && /opt/venv-mesh/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv-mesh/bin/pip install --no-cache-dir pymeshlab numpy

# 4. Instant Meshes — binário pré-compilado Linux x86_64
RUN wget -q "https://instant-meshes.s3.eu-central-1.amazonaws.com/instant-meshes-linux.zip" \
        -O /tmp/instant-meshes.zip \
    && unzip /tmp/instant-meshes.zip -d /opt/instant-meshes \
    && mv "/opt/instant-meshes/Instant Meshes" /opt/instant-meshes/InstantMeshes \
    && chmod +x /opt/instant-meshes/InstantMeshes \
    && ln -s /opt/instant-meshes/InstantMeshes /usr/local/bin/InstantMeshes \
    && rm /tmp/instant-meshes.zip

# 5. Scripts
WORKDIR /pipeline
COPY scripts/ ./scripts/
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

VOLUME ["/pipeline/input", "/pipeline/output"]

ENTRYPOINT ["/pipeline/entrypoint.sh"]