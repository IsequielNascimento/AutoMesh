"""
Passo 3/3 — Instant Meshes
Retopologia triangle com target vertex count configurável.
Exporta a mesh low-poly como .ply.
"""

import subprocess
import argparse


def run_instant_meshes(input_highpoly, output_lowpoly, target_vertices=80000):
    print(f"\n[3/3] Executando Instant Meshes...")
    print(f"      Entrada          : {input_highpoly}")
    print(f"      Saída            : {output_lowpoly}")
    print(f"      Target vértices  : {target_vertices:,}")

    im_cmd = [
        "InstantMeshes",
        "-o", output_lowpoly,
        "-v", str(target_vertices),
        input_highpoly,
    ]

    result = subprocess.run(im_cmd, check=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("[stderr]", result.stderr)

    print(f"[*] Instant Meshes finalizado → {output_lowpoly}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 3: Instant Meshes retopologia triangle")
    parser.add_argument("--input",    required=True,            help="Mesh high-poly .ply de entrada")
    parser.add_argument("--output",   required=True,            help="Mesh low-poly .ply de saída")
    parser.add_argument("--vertices", type=int, default=80000,  help="Target vertex count (padrão: 80000)")
    args = parser.parse_args()

    run_instant_meshes(
        input_highpoly  = args.input,
        output_lowpoly  = args.output,
        target_vertices = args.vertices,
    )