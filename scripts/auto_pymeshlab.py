"""
Passo 2/3 — PyMeshLab
Screened Poisson Surface Reconstruction + filtros de limpeza.
Exporta a mesh high-poly como .ply.
"""

import pymeshlab
import argparse


def run_pymeshlab(input_pc_ply, output_highpoly_ply, poisson_depth=10):
    print(f"\n[2/3] Executando PyMeshLab...")
    print(f"      Entrada       : {input_pc_ply}")
    print(f"      Saída         : {output_highpoly_ply}")
    print(f"      Poisson depth : {poisson_depth}")

    ms = pymeshlab.MeshSet()

    try:
        ms.load_new_mesh(input_pc_ply)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar {input_pc_ply}: {e}")

    m_in = ms.current_mesh()
    print(f"[*] Entrada: {m_in.vertex_number()} vértices, {m_in.face_number()} faces")

    print("[*] Calculando normais da nuvem de pontos...")
    ms.compute_normal_for_point_clouds(k=10, smoothiter=0)

    print(f"[*] Screened Poisson (depth={poisson_depth}) — pode demorar...")
    ms.generate_surface_reconstruction_screened_poisson(
        depth=poisson_depth,
        preclean=False,
        threads=0,           # 0 = usa todos os núcleos disponíveis
    )

    m_out = ms.current_mesh()
    print(f"[*] Saída bruta: {m_out.vertex_number()} vértices, {m_out.face_number()} faces")

    if m_out.vertex_number() == 0:
        raise RuntimeError(
            "Poisson não gerou malha. "
            "Verifique a densidade da nuvem de pontos de entrada."
        )

    print("[*] Limpando malha (duplicatas, vértices não referenciados)...")
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()

    m_clean = ms.current_mesh()
    print(f"[*] Saída limpa: {m_clean.vertex_number()} vértices, {m_clean.face_number()} faces")

    print(f"[*] Salvando → {output_highpoly_ply}")
    ms.save_current_mesh(
        output_highpoly_ply,
        save_vertex_color=True,
        save_vertex_normal=True,
    )
    print("[*] PyMeshLab finalizado!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Passo 2: PyMeshLab Screened Poisson + limpeza")
    parser.add_argument("--input",  required=True,        help="Nuvem de pontos .ply de entrada")
    parser.add_argument("--output", required=True,        help="Mesh high-poly .ply de saída")
    parser.add_argument("--depth",  type=int, default=10, help="Profundidade do Screened Poisson (padrão: 10)")
    args = parser.parse_args()

    run_pymeshlab(
        input_pc_ply      = args.input,
        output_highpoly_ply = args.output,
        poisson_depth     = args.depth,
    )