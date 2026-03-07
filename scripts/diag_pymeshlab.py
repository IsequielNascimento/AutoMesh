#!/usr/bin/env python3
"""Diagnóstico v2: testa Poisson com subsets menores da nuvem."""
import sys, resource
import pymeshlab

# Aumenta limite de stack para o processo
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    print(f"Stack limit: {soft} -> {hard}", flush=True)
except Exception as e:
    print(f"Stack limit unchanged: {e}", flush=True)

ply_file = sys.argv[1]
print(f"Arquivo: {ply_file}", flush=True)

for depth in [6, 7, 8]:
    print(f"\n--- Testando Poisson depth={depth} ---", flush=True)
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(ply_file)
    
    # Subsample agressivo para teste
    print(f"  Subsampling para reduzir pontos...", flush=True)
    ms.generate_simplified_point_cloud(samplenum=200000)
    ms.set_current_mesh(1)
    
    m = ms.current_mesh()
    print(f"  Pontos após subsample: {m.vertex_number():,}", flush=True)
    
    ms.compute_normal_for_point_clouds(k=10, smoothiter=0)
    print(f"  Normais OK. Rodando Poisson depth={depth}...", flush=True)
    
    try:
        ms.generate_surface_reconstruction_screened_poisson(
            depth=depth, preclean=False, threads=1
        )
        m2 = ms.current_mesh()
        print(f"  Poisson depth={depth} OK: {m2.vertex_number():,} verts, {m2.face_number():,} faces", flush=True)
        break
    except Exception as e:
        print(f"  ERRO depth={depth}: {e}", flush=True)