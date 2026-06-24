# Design Spec: Pipeline 3D Otimizado em C++ para AutoMesh

**Data:** 2026-06-24  
**Status:** Validado e Aguardando Revisão do Usuário  
**Autor:** Antigravity (AI Coding Assistant)  

---

## 1. Objetivo e Contexto

O projeto [AutoMesh](file:///e:/Programming%20Stuff/AutoMesh) é um pipeline de processamento de nuvens de pontos 3D (`.laz`) em malhas tridimensionais otimizadas (`low-poly`) em formato `.ply` voltadas para Realidade Aumentada na Web (WebAR). 

A arquitetura inicial utilizava scripts Python que atuavam como wrappers de pacotes de terceiros pesados (`PDAL`, `PyMeshLab` e `InstantMeshes` com dependências gráficas). Isso resultava em:
1. Imagens Docker gigantescas (>2.5 GB) devido ao uso de Python, Qt, OpenGL, X11 e simulação de vídeo virtual (`xvfb`).
2. Perda de cores do modelo 3D após a retopologia quadrangular.
3. Gargalos de desempenho e alto consumo de memória RAM devido a múltiplos wrappers.

Este documento de design propõe a **reconstrução completa do pipeline na linguagem C++ (Abordagem A)**, compilando apenas os algoritmos matemáticos essenciais e consolidando a etapa de colorização e entrega final diretamente no formato WebAR nativo (`.glb`).

---

## 2. Visão Geral da Arquitetura

O pipeline é transformado em um fluxo sequencial de quatro executáveis nativos leves:

```
[Entrada .laz] 
      │
      ▼
1. automesh-preproc (C++) ──► [passo1_nuvem.ply (filtrada, com normais e cores)]
      │ (filtra ruídos e estima normais usando LASlib + nanoflann + Eigen)
      ▼
2. PoissonReconstruction (C++) ──► [passo2_highpoly.ply (geometria densa triangulada)]
      │ (algoritmo oficial Screened Poisson de Kazhdan, sem dependências de GUI)
      ▼
3. InstantMeshes (C++ Headless) ──► [passo3_lowpoly.ply (geometria de poucos vértices)]
      │ (retopologia quadrangular/triangular, sem dependência gráfica)
      ▼
4. automesh-colortransfer (C++) ──► [resultado_final.glb (Malha final colorida)]
      │ (transfere cores da nuvem limpa do passo 1 e exporta em .glb usando tinygltf)
```

---

## 3. Especificação dos Componentes

### 3.1. `automesh-preproc` (Pré-processamento Customizado)
Substitui o `PDAL CLI`. É um utilitário escrito em C++ que lê nuvens de pontos `.laz` e gera um arquivo `.ply` contendo os pontos válidos, suas cores e vetores normais estimados.

* **Bibliotecas Utilizadas:**
  * **LASlib:** Leitura e descompressão direta de arquivos `.las` / `.laz`.
  * **nanoflann:** KD-Tree para busca rápida de vizinhos mais próximos.
  * **Eigen:** Álgebra linear para cálculo do menor autovetor (direção da normal).
* **Parâmetros de Entrada:**
  * `INPUT_FILE` (arquivo `.laz`)
  * `SPATIAL_SUBSAMPLE` (float - espaçamento mínimo em metros)
  * `SOR_NEIGHBORS` (int - número de vizinhos para detecção de ruído)
  * `SOR_STD` (float - multiplicador de desvio padrão do filtro SOR)
* **Algoritmo Interno:**
  1. Carrega todos os pontos com cores (RGB) em arrays na memória RAM.
  2. Executa Voxel Downsampling usando um dicionário hash (`std::unordered_map`) para indexar voxels 3D com base na resolução `SPATIAL_SUBSAMPLE`.
  3. Cria uma KD-Tree com os pontos do subsampling.
  4. Executa o filtro SOR (Statistical Outlier Removal) descartando pontos com distância média a vizinhos acima do limiar estatístico.
  5. Estima a normal de cada ponto sobrevivente montando a matriz de covariância 3x3 dos seus 10 vizinhos e extraindo o autovetor de menor autovalor (com o suporte do *Eigen*).
  6. Salva o resultado temporário em `passo1_nuvem.ply` contendo propriedades `x, y, z`, `nx, ny, nz`, `red, green, blue`.

---

### 3.2. `PoissonReconstruction` (Geração de Malha Densa)
Compilação direta do repositório oficial de Michael Kazhdan.
* **Repositório:** [mkazhdan/PoissonReconstruction](https://github.com/mkazhdan/PoissonReconstruction)
* **Executável:** `PoissonReconstruction`
* **Parâmetros:**
  * `--in /tmp/passo1_nuvem.ply`
  * `--out /tmp/passo2_highpoly.ply`
  * `--depth POISSON_DEPTH` (default: 10)
  * `--threads 1`
* **Vantagem:** Executa puramente em linha de comando, sem necessidade de janelas gráficas, gerando o mesh high-poly inicial (`passo2_highpoly.ply`) sem cores para otimizar processamento.

---

### 3.3. `InstantMeshes` (Retopologia Otimizada Headless)
Geração de malha com poucos vértices e topologia organizada.
* **Repositório:** [wjakob/instant-meshes](https://github.com/wjakob/instant-meshes)
* **Build Mode:** Compilação com a flag `-DINSTANT_MESHES_CLI=ON` (ou equivalente no CMake que remove GLFW e OpenGL).
* **Parâmetros:**
  * `-o /tmp/passo3_lowpoly.ply`
  * `-v TARGET_VERTICES` (default: 80000)
  * `/tmp/passo2_highpoly.ply`

---

### 3.4. `automesh-colortransfer` (Mapeamento de Cores e Exportação GLB)
Substitui as funções de transferência de cor do PyMeshLab e converte o resultado final de `.ply` para `.glb`.

* **Bibliotecas Utilizadas:**
  * **nanoflann:** KD-Tree para mapeamento geométrico rápido.
  * **tinygltf:** Geração e exportação do formato binário `.glb` (glTF 2.0).
* **Algoritmo Interno:**
  1. Carrega os pontos do `passo1_nuvem.ply` (nuvem com cores corretas) e monta uma KD-Tree 3D.
  2. Carrega a malha geométrica do `passo3_lowpoly.ply` (malha low-poly final, sem cor).
  3. Para cada vértice da malha low-poly:
     * Busca os vizinhos mais próximos na nuvem do `passo1_nuvem.ply`.
     * Interpola o valor de cor (RGB) dos vizinhos usando ponderação por inverso da distância (IDW - Inverse Distance Weighting).
     * Armazena a cor resultante nos atributos do vértice.
  4. Estrutura os dados no padrão glTF 2.0:
     * `POSITION` (array de floats XYZ)
     * `NORMAL` (array de floats NX NY NZ)
     * `COLOR_0` (array de floats/bytes RGB normalizado)
     * `indices` (array de inteiros definindo triângulos)
  5. Salva o resultado final diretamente como `/pipeline/output/resultado_final.glb`.

---

## 4. Estratégia de Build Docker e Otimização de Imagem

Para eliminar compiladores e dependências de build do container final, usaremos **Multi-Stage Build**:

### Fase 1: Build (Imagem Base: `ubuntu:22.04` ou similar com ferramentas de build)
1. Instalação de: `build-essential`, `cmake`, `git`, `libpng-dev`, `zlib1g-dev`.
2. Clone e compilação do `LASlib` em `/build/laslib`.
3. Clone e compilação de `PoissonReconstruction` em `/build/poisson`.
4. Clone e compilação de `InstantMeshes` em `/build/instantmeshes`.
5. Compilação dos nossos utilitários personalizados (`automesh-preproc` e `automesh-colortransfer`) linkando estaticamente com `LASlib`.

### Fase 2: Runtime (Imagem Base final: `ubuntu:22.04` limpa)
1. Copia apenas os binários gerados na Fase 1 para `/usr/local/bin/`:
   * `automesh-preproc`
   * `PoissonReconstruction`
   * `InstantMeshes`
   * `automesh-colortransfer`
2. Copia o arquivo [entrypoint.sh](file:///e:/Programming%20Stuff/AutoMesh/entrypoint.sh) simplificado.
3. Não há instalação de Python, pip, PyMeshLab, Xvfb, Mesa-GL, ou compiladores.

*Tamanho Final Projetado da Imagem:* **< 200 MB** (comparado aos atuais ~2.5 GB).

---

## 5. Plano de Verificação

### Testes Automatizados e de Pipeline
1. Executar o fluxo completo no docker com um arquivo `.laz` de teste.
2. Validar se o executável `resultado_final.glb` foi gerado e se abre em visualizadores web (ex: `model-viewer`).
3. Verificar a presença dos atributos de cores e se as cores estão posicionadas nos vértices corretos da malha.
4. Comparar o tempo total de processamento com o pipeline original em Python.
