import subprocess
import os
import glob

def run_cloudcompare(input_laz, output_ply):
    print("[1/4] Executando CloudCompare (SOR, Normais e Subsample)...")
    
    cc_cmd = [
        "CloudCompare", "-SILENT","-COMPUTE_NORMALS", "-O", input_laz,
        "-SOR", "20", "1.5",
        "-SS", "SPATIAL", "0.5",
        "-C_EXPORT_FMT", "PLY", "-SAVE_CLOUDS"
    ]
    subprocess.run(cc_cmd, check=True)
    
    # Extrai o nome do arquivo sem a extensão (ex: '1-points_RGB.laz' vira '1-points_RGB')
    base_name = os.path.splitext(input_laz)[0]
    
    # Cria o padrão de busca correto: '1-points_RGB_SOR_*.ply'
    search_pattern = f"{base_name}_SOR_*.ply"
    
    arquivos_gerados = glob.glob(search_pattern)
    
    if arquivos_gerados:
        arquivo_cc = max(arquivos_gerados, key=os.path.getctime)
        
        if os.path.exists(output_ply):
            os.remove(output_ply)
            
        os.rename(arquivo_cc, output_ply)
        print(f"[*] CloudCompare OK: Arquivo renomeado para '{output_ply}'")
    else:
        raise FileNotFoundError(f"Erro: O arquivo de saída do CloudCompare não foi encontrado com o padrão: {search_pattern}")
    


if __name__ == "__main__":
    LAZ_FILE = "1-points_RGB.laz"
    PC_PLY = "passo1_nuvem.ply"

    run_cloudcompare(LAZ_FILE, PC_PLY)

    print("Fase do CloudCompare concluída, prosseguindo para a próxima fase.")