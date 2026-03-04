import subprocess


def run_instant_meshes(input_highpoly, output_lowpoly, target_vertices=80000):
    print("[3/4] Executando Instant Meshes (Retopologia)...")
    #  -v define o target vertex count.
    im_cmd = [
        "InstantMeshes", 
        "-o", output_lowpoly,
        "-v", str(target_vertices),
        input_highpoly
    ]
    subprocess.run(im_cmd, check=True)






if __name__ == "__main__":

    HIGHPOLY_PLY = "passo2_highpoly.ply"
    LOWPOLY_PLY = "passo3_lowpoly.ply"
    FINAL_GLB = "modelo_webar_final.glb"

    run_instant_meshes(HIGHPOLY_PLY, LOWPOLY_PLY, target_vertices=80000)
    #run_blender_bake(HIGHPOLY_PLY, LOWPOLY_PLY, FINAL_GLB)
    
    print("Mesh Low Poly Criada")