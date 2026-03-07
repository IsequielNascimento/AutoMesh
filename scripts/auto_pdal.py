"""
Passo 1/3 — PDAL
Substitui o CloudCompare para leitura de .laz.
Operações equivalentes:
  - Statistical Outlier Removal (SOR)  → filters.outlier
  - Cálculo de normais                 → filters.normal
  - Subsampling espacial               → filters.voxeldownsize
Exporta a nuvem de pontos como .ply.
"""

import pdal
import json
import argparse
import os


def run_pdal(input_laz, output_ply, sor_neighbors=20, sor_std=1.5, spatial=0.5):
    print(f"\n[1/3] Executando PDAL...")
    print(f"      Entrada : {input_laz}")
    print(f"      Saída   : {output_ply}")
    print(f"      SOR     : vizinhos={sor_neighbors}, std={sor_std}")
    print(f"      Spatial : {spatial} m")

    os.makedirs(os.path.dirname(output_ply), exist_ok=True)

    # ------------------------------------------------------------------
    # Pipeline PDAL em JSON
    # Ordem: lê LAZ → SOR → voxel downsample → normais → escreve PLY
    # ------------------------------------------------------------------
    pipeline_def = {
        "pipeline": [
            # 1. Leitura do LAZ (LASzip nativo no PDAL)
            {
                "type": "readers.las",
                "filename": input_laz
            },

            # 2. Statistical Outlier Removal
            #    mean_k  = número de vizinhos (equivalente ao SOR do CloudCompare)
            #    multiplier = multiplicador do desvio padrão
            {
                "type": "filters.outlier",
                "method": "statistical",
                "mean_k": sor_neighbors,
                "multiplier": sor_std
            },

            # 3. Remove os pontos marcados como outliers pelo filtro acima
            {
                "type": "filters.range",
                "limits": "Classification![7:7]"  # 7 = noise/outlier no padrão LAS
            },

            # 4. Subsampling espacial (Voxel Grid)
            #    cell = tamanho da célula em metros
            {
                "type": "filters.voxeldownsize",
                "cell": spatial
            },

            # 5. Cálculo de normais (knn=10, equivalente ao CloudCompare)
            {
                "type": "filters.normal",
                "knn": 10
            },

            # 6. Exporta como PLY com todos os campos
            {
                "type": "writers.ply",
                "filename": output_ply,
                "storage_mode": "little endian",
                "dims": "X,Y,Z,Red,Green,Blue,NormalX,NormalY,NormalZ"
            }
        ]
    }

    pipeline_json = json.dumps(pipeline_def)

    print("[*] Executando pipeline PDAL (SOR + Voxel + Normais)...")
    pipeline = pdal.Pipeline(pipeline_json)
    pipeline.execute()

    count = pipeline.arrays[0].shape[0] if pipeline.arrays else 0
    print(f"[*] PDAL OK → {count:,} pontos exportados para '{output_ply}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 1: PDAL — SOR + Normais + Subsampling")
    parser.add_argument("--input",         required=True,         help="Arquivo .laz de entrada")
    parser.add_argument("--output",        required=True,         help="Arquivo .ply de saída")
    parser.add_argument("--sor-neighbors", type=int,   default=20,  help="SOR: número de vizinhos (padrão: 20)")
    parser.add_argument("--sor-std",       type=float, default=1.5, help="SOR: multiplicador de desvio padrão (padrão: 1.5)")
    parser.add_argument("--spatial",       type=float, default=0.5, help="Tamanho da célula voxel em metros (padrão: 0.5)")
    args = parser.parse_args()

    run_pdal(
        input_laz     = args.input,
        output_ply    = args.output,
        sor_neighbors = args.sor_neighbors,
        sor_std       = args.sor_std,
        spatial       = args.spatial,
    )
