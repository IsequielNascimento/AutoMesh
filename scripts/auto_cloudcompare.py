"""
Passo 1/3 — CloudCompare
Filtro SOR, cálculo de normais e subsampling espacial.
Exporta a nuvem de pontos como .ply.
"""

import subprocess
import os
import glob
import argparse


def run_cloudcompare(input_laz, output_ply, sor_neighbors=20, sor_std=1.5, spatial=0.5):
    print(f"\n[1/3] Executando CloudCompare...")
    print(f"      Entrada : {input_laz}")
    print(f"      Saída   : {output_ply}")
    print(f"      SOR     : vizinhos={sor_neighbors}, std={sor_std}")
    print(f"      Spatial : {spatial} m")

    cc_cmd = [
        "CloudCompare",
        "-SILENT",
        "-O", input_laz,
        "-SOR", str(sor_neighbors), str(sor_std),
        "-SS", "SPATIAL", str(spatial),
        "-COMPUTE_NORMALS",
        "-C_EXPORT_FMT", "PLY",
        "-SAVE_CLOUDS"
    ]

    subprocess.run(cc_cmd, check=True)

    base_name = os.path.splitext(input_laz)[0]
    search_pattern = f"{base_name}_SOR_*.ply"
    arquivos_gerados = glob.glob(search_pattern)

    if not arquivos_gerados:
        search_pattern = f"{base_name}*.ply"
        arquivos_gerados = glob.glob(search_pattern)

    if not arquivos_gerados:
        raise FileNotFoundError(
            f"Arquivo de saída do CloudCompare não encontrado. "
            f"Padrão buscado: {base_name}_SOR_*.ply"
        )

    arquivo_cc = max(arquivos_gerados, key=os.path.getctime)

    os.makedirs(os.path.dirname(output_ply), exist_ok=True)

    if os.path.exists(output_ply):
        os.remove(output_ply)

    os.rename(arquivo_cc, output_ply)
    print(f"[*] CloudCompare OK → '{output_ply}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 1: CloudCompare SOR + Normais + Subsample")
    parser.add_argument("--input",         required=True,         help="Arquivo .laz de entrada")
    parser.add_argument("--output",        required=True,         help="Arquivo .ply de saída")
    parser.add_argument("--sor-neighbors", type=int,   default=20,  help="SOR: número de vizinhos (padrão: 20)")
    parser.add_argument("--sor-std",       type=float, default=1.5, help="SOR: multiplicador de desvio padrão (padrão: 1.5)")
    parser.add_argument("--spatial",       type=float, default=0.5, help="Subsampling espacial em metros (padrão: 0.5)")
    args = parser.parse_args()

    run_cloudcompare(
        input_laz     = args.input,
        output_ply    = args.output,
        sor_neighbors = args.sor_neighbors,
        sor_std       = args.sor_std,
        spatial       = args.spatial,
    )