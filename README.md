# imghash - Documentación Completa

## Descripción

Herramienta para calcular hashes perceptuales de imágenes y encontrar duplicados o similares, incluso cuando han sido comprimidas (ej: enviadas por WhatsApp) o redimensionadas.

Optimizado para trabajar con grandes colecciones de imágenes (decenas de miles) usando índices de hashes para búsquedas rápidas.

## Archivos Incluidos

- `imghash.py` - Script principal en Python
- `imghash.1` - Página de manual (man page)
- `README.md` - Este archivo

---

## Instalación

### 1. Requisitos del sistema

El script requiere **Python 3.6 o superior**.

#### En Debian/Ubuntu/Linux Mint:

```bash
sudo apt update
sudo apt install python3 python3-pip
sudo apt install libjpeg-dev zlib1g-dev libtiff-dev libffi-dev libopenjp2-7
```

#### En Fedora/RHEL/CentOS:

```bash
sudo dnf install python3 python3-pip
sudo dnf install libjpeg-turbo-devel zlib-devel libtiff-devel
```

#### En Arch Linux:

```bash
sudo pacman -S python python-pil python-imagehash
```

#### En macOS:

```bash
brew install python3 python-pip
pip3 install imagehash
```

#### En Windows:

Descargar desde https://www.python.org/downloads/, luego:
```bash
pip install imagehash
```

### 2. Instalar dependencias de Python

```bash
pip3 install imagehash
```

### 3. Verificar instalación

```bash
python3 --version
python3 -c "import PIL; import imagehash; print('OK')"
python3 imghash.py --help
```

### 4. Hacer el script ejecutable (opcional)

```bash
chmod +x imghash.py
./imghash.py --help
```

---

## Uso

### Flujo de trabajo recomendado

```bash
# 1. Indexar carpeta principal con índice de hashes
python3 imghash.py --index /fotos -o indice.json --build-hash-index

# 2. Añadir más imágenes (incremental)
python3 imghash.py --index /mas_fotos --indice indice.json -o indice.json

# 3. Encontrar duplicados
python3 imghash.py --find-dups --i indice.json -o duplicados.json
python3 imghash.py --find-dups --i indice.json --threshold 90 -o dup90.json
```

### Comandos disponibles

| Comando | Descripción |
|---------|-------------|
| `--index CARPETA` | Indexar imágenes de una carpeta |
| `--build-hash-index` | Generar índice de hashes separado (más rápido) |
| `--find-dups` | Encontrar duplicados dentro del índice |
| `--search IMAGEN` | Buscar imagen específica en el índice |

### Opciones

| Opción | Descripción |
|--------|-------------|
| `--indice ARCHIVO` | Archivo de índice JSON |
| `--output ARCHIVO` | Archivo de salida JSON |
| `--threshold N` | % mínimo de similitud (0-100). Default: 85 para --find-dups |
| `--hash TIPO` | phash (default), ahash, dhash, whash |
| `--update` | Reindexar todo (ignora índice existente) |
| `--tamano N` | Tamaño para procesamiento (default: 32) |

---

## Ejemplos detallados

### 1. Indexación inicial

```bash
# Crear índice con índice de hashes para búsquedas rápidas
python3 imghash.py --index ~/Photos -o indice.json --build-hash-index
```

Esto genera:
- `indice.json` - Datos completos de cada imagen
- `indice_hash.json` - Solo hashes ordenados (archivo pequeño y rápido)

### 2. Añadir más imágenes

```bash
# Añadir imágenes de otra carpeta (incremental)
python3 imghash.py --index ~/Downloads/Images --indice indice.json -o indice.json
```

El script detecta qué imágenes ya están indexadas y solo procesa las nuevas.

### 3. Encontrar duplicados

```bash
# Con threshold por defecto (85%)
python3 imghash.py --find-dups --i indice.json -o duplicados.json

# Con threshold más alto (más estricto)
python3 imghash.py --find-dups --i indice.json --threshold 90 -o dup90.json

# Con threshold bajo (más permisivo)
python3 imghash.py --find-dups --i indice.json --threshold 70 -o dup70.json
```

### 4. Buscar una imagen específica

```bash
# Buscar todas las similares
python3 imghash.py --search foto.jpg --index indice.json -o resultados.json

# Buscar solo muy similares (>80%)
python3 imghash.py --search foto.jpg --index indice.json --threshold 80 -o resultados.json
```

### 5. Reindexar todo

```bash
# Recrear índice desde cero
python3 imghash.py --index ~/Photos --index indice.json --update -o indice.json --build-hash-index
```

---

## Rendimiento

### Para 10,000 imágenes

| Operación | Tiempo estimado |
|-----------|-----------------|
| Indexar | ~2-5 minutos |
| Generar hash index | ~1 segundo |
| Encontrar duplicados (con hash index) | ~2 segundos |
| Encontrar duplicados (sin hash index) | ~30 segundos |

### Optimización

El índice de hashes (`indice_hash.json`) es un archivo pequeño (~200KB para 10k imágenes) que permite búsquedas rápidas sin cargar el índice completo (~10MB+).

**Siempre usa `--build-hash-index`** cuando trabajes con muchas imágenes.

---

## Formato de Salida

### Índice (JSON)

```json
{
  "fecha_generacion": "2026-03-07T19:45:00",
  "carpeta_origen": "/ruta/a/imagenes",
  "tamano_procesamiento": 32,
  "total_imagenes": 150,
  "imagenes": [
    {
      "ruta": "/ruta/a/imagenes/foto1.jpg",
      "nombre": "foto1.jpg",
      "hashes": {
        "phash": "f2a8001c00000000",
        "ahash": "ffffffff00000000",
        "dhash": "ffffffff00000000",
        "whash": "f2a8001c00000000"
      },
      "hash_binario": "base64..."
    }
  ]
}
```

### Índice de hashes (JSON)

```json
{
  "tipo_hash": "phash",
  "fecha_generacion": "2026-03-07T19:45:00",
  "total": 150,
  "hashes": [
    {"hash": "aaa00000", "indice": 0},
    {"hash": "aaa10000", "indice": 15},
    {"hash": "bbb00000", "indice": 3}
  ]
}
```

### Duplicados (JSON)

```json
{
  "indice_utilizado": "hash_index",
  "tipo_hash": "phash",
  "threshold": 85,
  "distancia_maxima": 2,
  "grupos_similares": [
    {
      "id_grupo": 1,
      "tamano": 3,
      "imagenes": [
        {"ruta": "foto1.jpg", "nombre": "foto1.jpg", "distancia_hamming": 0, "similitud_pct": 100},
        {"ruta": "foto1_wp.jpg", "nombre": "foto1_wp.jpg", "distancia_hamming": 2, "similitud_pct": 87.5},
        {"ruta": "foto1_enviada.jpg", "nombre": "foto1_enviada.jpg", "distancia_hamming": 3, "similitud_pct": 81.25}
      ]
    },
    {
      "id_grupo": 2,
      "tamano": 2,
      "imagenes": [
        {"ruta": "img_a.jpg", "nombre": "img_a.jpg", "distancia_hamming": 0, "similitud_pct": 100},
        {"ruta": "img_b.jpg", "nombre": "img_b.jpg", "distancia_hamming": 1, "similitud_pct": 93.75}
      ]
    }
  ],
  "estadisticas": {
    "total_imagenes": 150,
    "total_grupos": 25,
    "imagenes_en_grupos": 48
  }
}
```

---

## Algoritmo

### Hash perceptual (phash)

1. Redimensionar imagen a 32x32
2. Convertir a escala de grises
3. Aplicar Transformada Discreta del Coseno (DCT)
4. Comparar coeficientes con la media
5. Generar hash binario

Esto produce un hash robusto que se mantiene similar tras compresión.

### Búsqueda de duplicados

1. Cargar índice de hashes (o generarlo)
2. Ordenar hashes lexicográficamente
3. Comparar solo elementos adyacentes
4. Agrupar los que tengan distancia ≤ threshold

**Complejidad:** O(n log n) vs O(n²) del método tradicional.

### Distancia Hamming

- 0 bits: idénticas
- 1-4 bits: muy similares (compresión diferente)
- 5-10 bits: similares (ediciones menores)
- >10 bits: diferentes

---

## Tipos de Hash

| Tipo | Descripción | Robustez |
|------|-------------|-----------|
| phash | Perceptual Hash (default) | Alta |
| ahash | Average Hash | Media |
| dhash | Difference Hash | Media-Alta |
| whash | Wavelet Hash | Alta |

**Recomendación:** Usa `phash` o `whash` para imágenes de WhatsApp.

---

## Instalación de la Página de Manual

```bash
sudo cp imghash.1 /usr/share/man/man1/
sudo mandb
man imghash
```

O ver sin instalar:
```bash
man -l imghash.1
```

---

*Generado el 7 de Marzo de 2026*
