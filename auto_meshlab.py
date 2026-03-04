import pymeshlab

def run_pymeshlab(input_pc_ply, output_highpoly_ply):
    print(f"\n[2/4] Executando PyMeshLab no arquivo: {input_pc_ply}")
    ms = pymeshlab.MeshSet()
    
    try:
        ms.load_new_mesh(input_pc_ply)
    except Exception as e:
        print(f"[!] Erro ao carregar o arquivo {input_pc_ply}: {e}")
        return

    # 1. Verifica Entrada
    m_in = ms.current_mesh()
    print(f"[*] Entrada: Nuvem carregada com {m_in.vertex_number()} vértices e {m_in.face_number()} faces.")

    # 2. Recalcula normais no PyMeshLab, dava erro com os normais do cloudcompare
    print("[*] Calculando/Ajustando normais da nuvem de pontos...")
    ms.compute_normal_for_point_clouds(k=10, smoothiter=0)

    # 3. Filtro para reconstruir a superficie (Poisson)
    print("[*] Executando Screened Poisson (Isso pode demorar dependendo da nuvem)...")
    ms.generate_surface_reconstruction_screened_poisson(depth=10, preclean=False, threads=12)

    m_out = ms.current_mesh()
    print(f"[*] Saída: Malha gerada com {m_out.vertex_number()} vértices e {m_out.face_number()} faces.")

    if m_out.vertex_number() == 0:
        print("[!] ERRO FATAL: O algoritmo de Poisson não conseguiu gerar a malha. Verifique a densidade da nuvem de pontos de entrada.")
        return

    # 4. Filstros de limpeza
    print("[*] Executando limpeza da malha...")
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()

    # 5. Exportação
    print(f"[*] Salvando arquivo em: {output_highpoly_ply}")
    ms.save_current_mesh(output_highpoly_ply, save_vertex_color=True, save_vertex_normal=True)
    print("[*] PyMeshLab finalizado com sucesso!\n")


if __name__ == "__main__":
    PC_PLY = "passo1_nuvem.ply"
    HIGHPOLY_PLY = "passo2_highpoly.ply"

    run_pymeshlab(PC_PLY, HIGHPOLY_PLY)