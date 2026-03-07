"""
Passo 2/3 — PyMeshLab
Screened Poisson Surface Reconstruction + limpeza da malha.
"""

import pymeshlab
import argparse
import resource
import sys


def set_unlimited_stack():
    """Screened Poisson é recursivo e precisa de muito stack. hotfix"""
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
        print(f"[*] Stack: {soft//1024//1024}MB -> {hard//1024//1024}MB", flush=True)
    except Exception as e:
        print(f"[*] Stack limit inalterado: {e}", flush=True)


def run_pymeshlab(input_pc_ply, output_highpoly_ply, poisson_depth=10):
    set_unlimited_stack()

    print(f"\n[2/3] Executando PyMeshLab...")
    print(f"      Entrada       : {input_pc_ply}")
    print(f"      Saída         : {output_highpoly_ply}")
    print(f"      Poisson depth : {poisson_depth}")
    sys.stdout.flush()

    ms = pymeshlab.MeshSet()

    try:
        ms.load_new_mesh(input_pc_ply)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar {input_pc_ply}: {e}")

    m_in = ms.current_mesh()
    n_pts = m_in.vertex_number()
    print(f"[*] Entrada: {n_pts:,} vértices, {m_in.face_number():,} faces", flush=True)

    # Screened Poisson com 2.4M pontos causa segfault.
    MAX_POINTS = 500_000
    if n_pts > MAX_POINTS:
        print(f"[*] Nuvem grande ({n_pts:,} pts). Subsampling para {MAX_POINTS:,}...", flush=True)
        ms.generate_simplified_point_cloud(samplenum=MAX_POINTS)
        ms.set_current_mesh(ms.mesh_number() - 1)
        m_in = ms.current_mesh()
        print(f"[*] Após subsample: {m_in.vertex_number():,} vértices", flush=True)

    print("[*] Calculando normais...", flush=True)
    ms.compute_normal_for_point_clouds(k=10, smoothiter=0)

    print(f"[*] Screened Poisson (depth={poisson_depth}, threads=1)...", flush=True)
    sys.stdout.flush()
    ms.generate_surface_reconstruction_screened_poisson(
        depth=poisson_depth,
        preclean=False,
        threads=1,
    )

    m_out = ms.current_mesh()
    print(f"[*] Saída bruta: {m_out.vertex_number():,} vértices, {m_out.face_number():,} faces", flush=True)

    if m_out.vertex_number() == 0:
        raise RuntimeError("Poisson não gerou malha.")

    print("[*] Limpando malha...", flush=True)
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()

    m_clean = ms.current_mesh()
    print(f"[*] Saída limpa: {m_clean.vertex_number():,} vértices, {m_clean.face_number():,} faces", flush=True)

    print(f"[*] Salvando → {output_highpoly_ply}", flush=True)
    ms.save_current_mesh(
        output_highpoly_ply,
        save_vertex_color=True,
        save_vertex_normal=True,
    )
    print("[*] PyMeshLab finalizado!", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--depth",  type=int, default=10)
    args = parser.parse_args()

    run_pymeshlab(args.input, args.output, args.depth)