#!/bin/bash
# Entrypoint: Pipeline 3D
# PDAL CLI → PyMeshLab → Instant Meshes
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

PYTHON_SYS="python3"
PYTHON_MESH="/opt/venv-mesh/bin/python3"

TARGET_VERTICES="${TARGET_VERTICES:-80000}"
POISSON_DEPTH="${POISSON_DEPTH:-10}"
SOR_NEIGHBORS="${SOR_NEIGHBORS:-20}"
SOR_STD="${SOR_STD:-1.5}"
SPATIAL_SUBSAMPLE="${SPATIAL_SUBSAMPLE:-0.5}"

INPUT_DIR="/pipeline/input"
OUTPUT_DIR="/pipeline/output"
STEP1_PLY="${OUTPUT_DIR}/passo1_nuvem.ply"
STEP2_PLY="${OUTPUT_DIR}/passo2_highpoly.ply"
STEP3_PLY="${OUTPUT_DIR}/passo3_lowpoly.ply"

echo ""
echo "============================================================"
echo "  Pipeline 3D: LAZ → PLY → High Poly → Low Poly"
echo "============================================================"

# Detecta arquivo de entrada
if [ -z "$INPUT_FILE" ]; then
    INPUT_LAZ=$(find "$INPUT_DIR" -maxdepth 1 -name "*.laz" | head -1)
    [ -z "$INPUT_LAZ" ] && log_error "Nenhum .laz encontrado em $INPUT_DIR"
    log_warn "INPUT_FILE não definido. Usando: $INPUT_LAZ"
else
    INPUT_LAZ="${INPUT_DIR}/${INPUT_FILE}"
    [ ! -f "$INPUT_LAZ" ] && log_error "Arquivo não encontrado: $INPUT_LAZ"
fi

log_info "Entrada           : $INPUT_LAZ"
log_info "Target vértices   : $TARGET_VERTICES"
log_info "Poisson depth     : $POISSON_DEPTH"
log_info "SOR (viz/std)     : $SOR_NEIGHBORS / $SOR_STD"
log_info "Spatial subsample : $SPATIAL_SUBSAMPLE m"
echo ""

# PASSO 1 — PDAL CLI (python3 do sistema, sem binding)
echo "------------------------------------------------------------"
log_info "[1/3] PDAL — SOR + Normais + Voxel Subsample → PLY"
echo "------------------------------------------------------------"

"$PYTHON_SYS" /pipeline/scripts/auto_pdal.py \
    --input         "$INPUT_LAZ" \
    --output        "$STEP1_PLY" \
    --sor-neighbors "$SOR_NEIGHBORS" \
    --sor-std       "$SOR_STD" \
    --spatial       "$SPATIAL_SUBSAMPLE"

log_success "Passo 1 concluído → $STEP1_PLY"
echo ""

# DIAGNÓSTICO — testa pymeshlab antes de rodar
echo "------------------------------------------------------------"
log_info "[DIAG] Testando pymeshlab passo a passo..."
echo "------------------------------------------------------------"
xvfb-run --auto-servernum --server-args="-screen 0 1024x768x24" \
    "$PYTHON_MESH" /pipeline/scripts/diag_pymeshlab.py "$STEP1_PLY" || true
echo ""

# PASSO 2 — PyMeshLab (venv isolado)
echo "------------------------------------------------------------"
log_info "[2/3] PyMeshLab — Screened Poisson + Limpeza → PLY"
echo "------------------------------------------------------------"

# Aumenta stack limit (Poisson pode precisar de muito stack)
ulimit -s unlimited
xvfb-run --auto-servernum --server-args="-screen 0 1024x768x24" \
    "$PYTHON_MESH" /pipeline/scripts/auto_pymeshlab.py \
    --input  "$STEP1_PLY" \
    --output "$STEP2_PLY" \
    --depth  "$POISSON_DEPTH"

log_success "Passo 2 concluído → $STEP2_PLY"
echo ""

# PASSO 3 — Instant Meshes
echo "------------------------------------------------------------"
log_info "[3/3] Instant Meshes — Retopologia Triangle → PLY"
echo "------------------------------------------------------------"

InstantMeshes \
    -o "$STEP3_PLY" \
    -v "$TARGET_VERTICES" \
    "$STEP2_PLY"

log_success "Passo 3 concluído → $STEP3_PLY"
echo ""

echo "============================================================"
log_success "PIPELINE CONCLUÍDO!"
echo ""
ls -lh "$OUTPUT_DIR"/*.ply 2>/dev/null || true
echo "============================================================"