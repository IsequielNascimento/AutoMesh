#!/bin/bash
# ============================================================
# Entrypoint: Pipeline 3D Automatizado
# PDAL → PyMeshLab → Instant Meshes
# ============================================================
set -e

# --- Cores para output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

# Lê variáveis de ambiente (com valores padrão)
INPUT_LAZ="${INPUT_FILE:-}"                          # ex: minha_nuvem.laz
TARGET_VERTICES="${TARGET_VERTICES:-80000}"          # vértices alvo no Instant Meshes
POISSON_DEPTH="${POISSON_DEPTH:-10}"                 # profundidade do Screened Poisson
SOR_NEIGHBORS="${SOR_NEIGHBORS:-20}"                 # SOR: nº de vizinhos
SOR_STD="${SOR_STD:-1.5}"                            # SOR: multiplicador de desvio padrão
SPATIAL_SUBSAMPLE="${SPATIAL_SUBSAMPLE:-0.5}"        # Subsampling espacial (metros)

INPUT_DIR="/pipeline/input"

# Suprime warning "pj_obj_create: Open of /opt/conda/share/proj failed"
export PROJ_DATA="/opt/conda/share/proj"
OUTPUT_DIR="/pipeline/output"

STEP1_PLY="${OUTPUT_DIR}/passo1_nuvem.ply"
STEP2_PLY="${OUTPUT_DIR}/passo2_highpoly.ply"
STEP3_PLY="${OUTPUT_DIR}/passo3_lowpoly.ply"

echo ""
echo "============================================================"
echo "  Pipeline 3D: LAZ → PLY → High Poly → Low Poly"
echo "============================================================"

# Valida arquivo de entrada
if [ -z "$INPUT_FILE" ]; then
    # Tenta encontrar automaticamente um .laz no /input
    INPUT_LAZ=$(find "$INPUT_DIR" -maxdepth 1 -name "*.laz" | head -1)
    if [ -z "$INPUT_LAZ" ]; then
        log_error "Nenhum arquivo .laz encontrado em $INPUT_DIR e INPUT_FILE não foi definido."
    fi
    log_warn "INPUT_FILE não definido. Usando: $INPUT_LAZ"
else
    INPUT_LAZ="${INPUT_DIR}/${INPUT_FILE}"
    if [ ! -f "$INPUT_LAZ" ]; then
        log_error "Arquivo não encontrado: $INPUT_LAZ"
    fi
fi

log_info "Arquivo de entrada : $INPUT_LAZ"
log_info "Target vértices    : $TARGET_VERTICES"
log_info "Poisson depth      : $POISSON_DEPTH"
log_info "SOR (viz/std)      : $SOR_NEIGHBORS / $SOR_STD"
log_info "Spatial subsample  : $SPATIAL_SUBSAMPLE m"
echo ""

# PASSO 1 — PDAL
echo "------------------------------------------------------------"
log_info "[1/3] PDAL — SOR + Normais + Voxel Subsample → PLY"
echo "------------------------------------------------------------"

python3 /pipeline/scripts/auto_pdal.py \
    --input  "$INPUT_LAZ" \
    --output "$STEP1_PLY" \
    --sor-neighbors "$SOR_NEIGHBORS" \
    --sor-std       "$SOR_STD" \
    --spatial       "$SPATIAL_SUBSAMPLE"

log_success "Passo 1 concluído → $STEP1_PLY"
echo ""

# PASSO 2 — PyMeshLab
echo "------------------------------------------------------------"
log_info "[2/3] PyMeshLab — Screened Poisson + Limpeza → PLY"
echo "------------------------------------------------------------"

# Roda pymeshlab com LD_PRELOAD da libstdc++ do conda para evitar segfault
# causado por conflito entre libstdc++/libgomp do conda vs sistema.
LD_PRELOAD="/opt/conda/lib/libstdc++.so.6:/opt/conda/lib/libgomp.so.1" \
LD_LIBRARY_PATH="/opt/conda/lib" \
/opt/conda/bin/python3 /pipeline/scripts/auto_pymeshlab.py \
    --input  "$STEP1_PLY" \
    --output "$STEP2_PLY" \
    --depth  "$POISSON_DEPTH"

log_success "Passo 2 concluído → $STEP2_PLY"
echo ""

# PASSO 3 — Instant Meshes
echo "------------------------------------------------------------"
log_info "[3/3] Instant Meshes — Retopologia Triangle → PLY"
echo "------------------------------------------------------------"

/opt/conda/bin/python3 /pipeline/scripts/auto_instantmesh.py \
    --input    "$STEP2_PLY" \
    --output   "$STEP3_PLY" \
    --vertices "$TARGET_VERTICES"

log_success "Passo 3 concluído → $STEP3_PLY"
echo ""

# Resumo final
echo "============================================================"
log_success "PIPELINE CONCLUÍDO COM SUCESSO!"
echo ""
echo "  Arquivos gerados em: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/*.ply 2>/dev/null || true
echo "============================================================"
echo ""