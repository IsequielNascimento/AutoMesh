"""
Passo 1/3 — PDAL CLI
Gera um pipeline JSON e executa via `pdal pipeline`.
Sem dependência de binding Python — usa apenas o binário pdal do sistema.

Operações:
  - readers.las       → lê .laz/.las com LASzip nativo
  - filters.outlier   → Statistical Outlier Removal (SOR)
  - filters.range     → remove pontos marcados como noise
  - filters.voxeldownsize → subsampling espacial
  - filters.normal    → calcula normais
  - writers.ply       → exporta PLY com X,Y,Z,RGB,Normais
"""

import subprocess
import json
import argparse
import os
import tempfile


def run_pdal(input_laz, output_ply, sor_neighbors=20, sor_std=1.5, spatial=0.5):
    print(f"\n[1/3] Executando PDAL CLI...")
    print(f"      Entrada : {input_laz}")
    print(f"      Saída   : {output_ply}")
    print(f"      SOR     : vizinhos={sor_neighbors}, std={sor_std}")
    print(f"      Spatial : {spatial} m")

    os.makedirs(os.path.dirname(output_ply), exist_ok=True)

    pipeline = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": input_laz
            },
            {
                "type": "filters.outlier",
                "method": "statistical",
                "mean_k": sor_neighbors,
                "multiplier": sor_std
            },
            {
                "type": "filters.range",
                "limits": "Classification![7:7]"
            },
            {
                "type": "filters.voxeldownsize",
                "cell": spatial
            },
            {
                "type": "filters.normal",
                "knn": 10
            },
            {
                "type": "writers.ply",
                "filename": output_ply,
                "storage_mode": "little endian",
                "dims": "X,Y,Z,Red,Green,Blue,NormalX,NormalY,NormalZ"
            }
        ]
    }

    # Escreve o JSON num arquivo temporário e passa para `pdal pipeline`
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(pipeline, f, indent=2)
        pipeline_file = f.name

    try:
        print("[*] Executando: pdal pipeline ...")
        result = subprocess.run(
            ["pdal", "pipeline", pipeline_file],
            capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"pdal pipeline falhou com código {result.returncode}")
    finally:
        os.unlink(pipeline_file)

    if not os.path.exists(output_ply):
        raise RuntimeError(f"Arquivo de saída não gerado: {output_ply}")

    size_mb = os.path.getsize(output_ply) / 1024 / 1024
    print(f"[*] PDAL OK → '{output_ply}' ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 1: PDAL CLI")
    parser.add_argument("--input",         required=True)
    parser.add_argument("--output",        required=True)
    parser.add_argument("--sor-neighbors", type=int,   default=20)
    parser.add_argument("--sor-std",       type=float, default=1.5)
    parser.add_argument("--spatial",       type=float, default=0.5)
    args = parser.parse_args()

    run_pdal(args.input, args.output, args.sor_neighbors, args.sor_std, args.spatial)