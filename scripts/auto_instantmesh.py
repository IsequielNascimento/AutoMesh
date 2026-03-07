"""
Passo 3/3 — Instant Meshes
Retopologia triangle com target vertex count configurável.
"""

import subprocess
import argparse


def run_instant_meshes(input_highpoly, output_lowpoly, target_vertices=80000):
    print(f"\n[3/3] Executando Instant Meshes...")
    print(f"      Entrada         : {input_highpoly}")
    print(f"      Saída           : {output_lowpoly}")
    print(f"      Target vértices : {target_vertices:,}")

    result = subprocess.run(
        ["InstantMeshes", "-o", output_lowpoly, "-v", str(target_vertices), input_highpoly],
        capture_output=True, text=True
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("[stderr]", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"InstantMeshes falhou com código {result.returncode}")

    print(f"[*] Instant Meshes finalizado → {output_lowpoly}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 3: Instant Meshes")
    parser.add_argument("--input",    required=True)
    parser.add_argument("--output",   required=True)
    parser.add_argument("--vertices", type=int, default=80000)
    args = parser.parse_args()

    run_instant_meshes(args.input, args.output, args.vertices)