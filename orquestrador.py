import os
import auto_cloudcompare
import auto_pymeshlab
import auto_instantmesh

# Os caminhos agora apontam para a pasta "/dados", que será mapeada do seu PC
PASTA_DADOS = "/dados"
LAZ_FILE = os.path.join(PASTA_DADOS, "monolito_bruto.laz")
PC_PLY = os.path.join(PASTA_DADOS, "passo1_nuvem.ply")
HIGHPOLY_PLY = os.path.join(PASTA_DADOS, "passo2_highpoly.ply")
LOWPOLY_PLY = os.path.join(PASTA_DADOS, "passo3_lowpoly.ply")

def main():
    print("=== INICIANDO PIPELINE GEOPARQUE NO DOCKER ===")
    
    if not os.path.exists(LAZ_FILE):
        print(f"[!] ERRO: Arquivo de entrada {LAZ_FILE} não encontrado no volume.")
        return

    # Passo 1
    auto_cloudcompare.run_cloudcompare(LAZ_FILE, PC_PLY)
    
    # Passo 2
    auto_pymeshlab.run_pymeshlab(PC_PLY, HIGHPOLY_PLY)
    
    # Passo 3
    auto_instantmesh.run_instant_meshes(HIGHPOLY_PLY, LOWPOLY_PLY, target_vertices=60000)
    
    print("=== PIPELINE CONCLUÍDA! Verifique a pasta no seu computador. ===")

if __name__ == "__main__":
    main()