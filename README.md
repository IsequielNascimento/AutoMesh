# Pipeline 3D Automatizado — Docker

Automatiza o processamento de nuvens de pontos `.laz` em meshes low-poly `.ply` prontas para WebAR.

```
LAZ  →  [CloudCompare]  →  PLY (nuvem limpa)
     →  [PyMeshLab]     →  PLY (high-poly)
     →  [Instant Meshes]→  PLY (low-poly final)
```

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20
- ~16 GB de RAM disponível (recomendado para Poisson em nuvens densas)

---

## Estrutura de pastas

```
AutoMesh/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example          ← copie para .env e configure
├── scripts/
│   ├── auto_cloudcompare.py
│   ├── auto_pymeshlab.py
│   └── auto_instantmesh.py
├── input/                ← coloque seu .laz aqui
└── output/               ← resultados gerados aqui
```

---

## Como usar

### 1. Prepare o ambiente

```bash
# Clone / copie os arquivos do projeto
cd AutoMesh

# Crie as pastas de I/O
mkdir -p input output

# Configure o arquivo de ambiente
cp .env.example .env
# Edite .env e ajuste INPUT_FILE e demais parâmetros
```

### 2. Coloque o arquivo .laz na pasta `input/`

```bash
cp /caminho/para/seu/arquivo.laz ./input/
```

### 3. Build (apenas na primeira vez ou após mudanças)

```bash
docker compose build
```

> O build baixa e instala CloudCompare, PyMeshLab e Instant Meshes automaticamente.
> Isso pode levar alguns minutos na primeira execução.

### 4. Execute o pipeline

```bash
docker compose up
```

Os arquivos gerados estarão em `./output/`:

| Arquivo                  | Descrição                            |
|--------------------------|--------------------------------------|
| `passo1_nuvem.ply`       | Nuvem filtrada (SOR + normais)       |
| `passo2_highpoly.ply`    | Mesh high-poly (Screened Poisson)    |
| `passo3_lowpoly.ply`     | Mesh low-poly final (retopologia)    |

---

## Parâmetros configuráveis

Edite o arquivo `.env` ou a seção `environment` do `docker-compose.yml`:

| Variável           | Padrão | Descrição                                      |
|--------------------|--------|------------------------------------------------|
| `INPUT_FILE`       | —      | Nome do `.laz` dentro de `./input/` (obrigatório) |
| `TARGET_VERTICES`  | 80000  | Vértices alvo no Instant Meshes                |
| `POISSON_DEPTH`    | 10     | Profundidade do Screened Poisson (8–12)        |
| `SOR_NEIGHBORS`    | 20     | Vizinhos do filtro SOR (CloudCompare)          |
| `SOR_STD`          | 1.5    | Desvio padrão do SOR (menor = mais agressivo)  |
| `SPATIAL_SUBSAMPLE`| 0.5   | Espaçamento mínimo entre pontos (metros)       |

### Exemplo: nuvem muito densa, retopologia mais leve

```env
INPUT_FILE=scan_denso.laz
POISSON_DEPTH=12
TARGET_VERTICES=50000
SPATIAL_SUBSAMPLE=0.3
```

---

## Executar via `docker run` (sem Compose)

```bash
docker build -t AutoMesh .

docker run --rm \
  -v $(pwd)/input:/pipeline/input:ro \
  -v $(pwd)/output:/pipeline/output:rw \
  -e INPUT_FILE="minha_nuvem.laz" \
  -e TARGET_VERTICES="80000" \
  AutoMesh
```

---

## Solução de problemas

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| `Arquivo não encontrado` | INPUT_FILE errado | Confira o nome exato em `./input/` |
| Poisson gera 0 vértices | Nuvem muito esparsa | Reduza `SPATIAL_SUBSAMPLE` |
| Poisson lento demais | Depth muito alto | Reduza `POISSON_DEPTH` para 8 |
| Container sem memória | RAM insuficiente | Aumente o limite em `docker-compose.yml` |
| `InstantMeshes: command not found` | Build incompleto | Rode `docker compose build --no-cache` |

---

## Ferramentas instaladas no container

| Ferramenta    | Versão / Fonte                          |
|---------------|-----------------------------------------|
| CloudCompare  | Ubuntu 22.04 apt (`cloudcompare`)       |
| PyMeshLab     | PyPI (`pip install pymeshlab`)          |
| Instant Meshes| Binário oficial Linux (S3 da AWS)       |
| Python        | 3.10 (Ubuntu 22.04 padrão)              |
