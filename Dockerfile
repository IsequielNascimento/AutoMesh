# ============================================================
# Pipeline 3D: PDAL → PyMeshLab → Instant Meshes
# Base: mambaforge (conda-forge)
# ============================================================
FROM condaforge/mambaforge:latest

ENV DEBIAN_FRONTEND=noninteractive

# 0. Libs de sistema para libGL (pymeshlab) e Instant Meshes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 1. Conda: pdal + python-pdal + libstdcxx-ng atualizado

RUN mamba install -y -c conda-forge \
        pdal \
        python-pdal \
        numpy \
        libstdcxx-ng \
    && conda clean -afy

# 2. pymeshlab via pip

ENV LD_LIBRARY_PATH="/opt/conda/lib:${LD_LIBRARY_PATH}"

RUN pip install --no-cache-dir pymeshlab

# 3. Instant Meshes — binário pré-compilado Linux x86_64
RUN wget -q "https://instant-meshes.s3.eu-central-1.amazonaws.com/instant-meshes-linux.zip" \
        -O /tmp/instant-meshes.zip \
    && unzip /tmp/instant-meshes.zip -d /opt/instant-meshes \
    && mv "/opt/instant-meshes/Instant Meshes" /opt/instant-meshes/InstantMeshes \
    && chmod +x /opt/instant-meshes/InstantMeshes \
    && ln -s /opt/instant-meshes/InstantMeshes /usr/local/bin/InstantMeshes \
    && rm /tmp/instant-meshes.zip

# 4. Scripts do pipeline
WORKDIR /pipeline
COPY scripts/ ./scripts/

# 5. Volumes de I/O
VOLUME ["/pipeline/input", "/pipeline/output"]

# 6. Entrypoint
COPY entrypoint.sh /pipeline/entrypoint.sh
RUN chmod +x /pipeline/entrypoint.sh

ENTRYPOINT ["/pipeline/entrypoint.sh"]