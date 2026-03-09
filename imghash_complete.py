#!/usr/bin/env python3
"""
imghash - Hash perceptual de imágenes para encontrar duplicados o similares

Este programa calcula hashes perceptuales de imágenes y encuentra duplicados
o imágenes similares, incluso cuando han sido comprimidas (ej: enviadas por
WhatsApp) o redimensionadas.

Uso:
    python3 imghash.py --index /carpeta/imagenes -o indice.json
    python3 imghash.py --search foto.jpg --i indice.json -o resultados.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import imagehash
from PIL import Image
import base64


def procesar_imagen(ruta_img, tamano=32):
    img = Image.open(ruta_img)
    img_gray = img.convert('L')
    img_resized = img_gray.resize((tamano, tamano), Image.LANCZOS)
    img_binaria = img_resized.point(lambda x: 255 if x >= 128 else 0)
    return img_binaria


def calcular_hashes(ruta_img):
    img = Image.open(ruta_img)
    hashes = {
        'phash': str(imagehash.phash(img)),
        'ahash': str(imagehash.average_hash(img)),
        'dhash': str(imagehash.dhash(img)),
        'whash': str(imagehash.whash(img))
    }
    return hashes


def cargar_indice(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r') as f:
        return json.load(f)


def guardar_indice(data, filepath):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def indexar_carpeta(carpeta, tamano=32):
    carpeta_path = Path(carpeta)
    if not carpeta_path.exists():
        print(f"Error: La carpeta '{carpeta}' no existe", file=sys.stderr)
        sys.exit(1)
    
    extensiones = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    imagenes = []
    
    archivos = list(carpeta_path.rglob('*'))
    total = len([a for a in archivos if a.suffix.lower() in extensiones])
    
    print(f"Indexando {total} imágenes de '{carpeta}'...")
    
    for i, archivo in enumerate(archivos):
        if archivo.suffix.lower() not in extensiones:
            continue
        
        try:
            hashes = calcular_hashes(archivo)
            img_binaria = procesar_imagen(archivo, tamano)
            bytes_img = img_binaria.tobytes()
            hash_binario = base64.b64encode(bytes_img).decode('utf-8')
            
            imagenes.append({
                'ruta': str(archivo.absolute()),
                'nombre': archivo.name,
                'hashes': hashes,
                'hash_binario': hash_binario,
                'tamano_procesado': tamano
            })
            
            if (i + 1) % 50 == 0:
                print(f"  Procesadas: {i + 1}/{total}")
                
        except Exception as e:
            print(f"  Error con {archivo}: {e}", file=sys.stderr)
    
    print(f"  Total indexadas: {len(imagenes)}")
    
    return {
        'fecha_generacion': datetime.now().isoformat(),
        'carpeta_origen': str(carpeta_path.absolute()),
        'tamano_procesamiento': tamano,
        'total_imagenes': len(imagenes),
        'imagenes': imagenes
    }


def distancia_hamming(hash1, hash2):
    if len(hash1) != len(hash2):
        return 999
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def calcular_similitud(hash1, hash2):
    dist = distancia_hamming(hash1, hash2)
    longitud = max(len(hash1), len(hash2))
    return round((1 - dist / longitud) * 100, 2)


def buscar_similares(indice, objetivo_path, threshold=0, hash_type='phash'):
    if not os.path.exists(objetivo_path):
        print(f"Error: La imagen '{objetivo_path}' no existe", file=sys.stderr)
        sys.exit(1)
    
    hashes_obj = calcular_hashes(objetivo_path)
    hash_obj = hashes_obj.get(hash_type, '')
    
    if not hash_obj:
        print(f"Error: No se pudo calcular {hash_type} para la imagen objetivo", file=sys.stderr)
        sys.exit(1)
    
    resultados = []
    
    for img in indice.get('imagenes', []):
        hash_img = img.get('hashes', {}).get(hash_type, '')
        if not hash_img:
            continue
        
        dist = distancia_hamming(hash_obj, hash_img)
        similitud = calcular_similitud(hash_obj, hash_img)
        
        if similitud >= threshold:
            resultados.append({
                'ruta': img['ruta'],
                'nombre': img['nombre'],
                'distancia_hamming': dist,
                'similitud_pct': similitud,
                'hash': hash_img
            })
    
    resultados.sort(key=lambda x: x['distancia_hamming'])
    
    return {
        'objetivo': objetivo_path,
        'hash_objetivo': hash_obj,
        'tipo_hash': hash_type,
        'threshold': threshold,
        'similares': resultados
    }


def main():
    parser = argparse.ArgumentParser(
        description='Hash de imágenes para encontrar duplicados/similares'
    )
    parser.add_argument('--index', metavar='CARPETA', 
                        help='Carpeta a indexar')
    parser.add_argument('--search', metavar='IMAGEN',
                        help='Buscar imagen similar en el índice')
    parser.add_argument('--i', '--indice', dest='indice', metavar='INDICE.JSON',
                        help='Fichero de índice (JSON)')
    parser.add_argument('-o', '--output', metavar='SALIDA.JSON',
                        help='Fichero de salida (JSON)')
    parser.add_argument('--threshold', type=int, default=0,
                        help='Umbral mínimo de similitud (0-100)')
    parser.add_argument('--hash', dest='hash_type', 
                        choices=['phash', 'ahash', 'dhash', 'whash'], 
                        default='phash',
                        help='Tipo de hash a usar para comparación')
    parser.add_argument('--tamano', type=int, default=32,
                        help='Tamaño para procesamiento binario (default: 32)')
    
    args = parser.parse_args()
    
    output_file = args.output or 'resultado.json'
    
    if args.index:
        indice = indexar_carpeta(args.index, args.tamano)
        guardar_indice(indice, output_file)
        print(f"Índice guardado en: {output_file}")
        
    elif args.search and args.indice:
        indice = cargar_indice(args.indice)
        if not indice:
            print(f"Error: No se pudo cargar el índice '{args.indice}'", file=sys.stderr)
            sys.exit(1)
        
        resultados = buscar_similares(indice, args.search, args.threshold, args.hash_type)
        guardar_indice(resultados, output_file)
        print(f"Encontradas {len(resultados['similares'])} imágenes similares")
        print(f"Resultados guardados en: {output_file}")
        
    else:
        parser.print_help()
        print("\nEjemplos:")
        print("  python imghash.py --index /fotos/ -o indice.json")
        print("  python imghash.py --search foto.jpg --i indice.json -o resultados.json")
        print("  python imghash.py --search foto.jpg --i indice.json --threshold 80 -o resultados.json")


if __name__ == '__main__':
    main()






'''
=============================================================================
SECCIÓN 2: PÁGINA DE MANUAL (imghash.1)
=============================================================================

.TH IMGHASH 1 "Marzo 2026"
.SH NAME
imghash \- Hash perceptual de imágenes para encontrar duplicados o similares
.SH SYNOPSIS
.B imghash
[\fB\-\-index\fR \fICARPETA\fR]
[\fB\-\-search\fR \fIIMAGEN\fR]
[\fB\-i\fR|\fB\-\-indice\fR \fIINDICE.JSON\fR]
[\fB\-o\fR|\fB\-\-output\fR \fISALIDA.JSON\fR]
[\fB\-\-threshold\fR \fIN\fR]
[\fB\-\-hash\fR \fITIPO\fR]
[\fB\-\-tamano\fR \fIN\fR]
.SH DESCRIPCIÓN
\fBimghash\fR es una herramienta para calcular hashes perceptuales de imágenes
y encontrar duplicados o imágenes similares, incluso cuando han sido
comprimidas (ej: enviadas por WhatsApp) o redimensionadas.
.PP
El programa funciona en dos fases:
.IP 1. 3
\fBIndexación\fR: Calcula hashes de todas las imágenes en una carpeta y
los guarda en un archivo JSON.
.IP 2. 3
\fBBúsqueda\fR: Compara una imagen objetivo contra el índice y encuentra
las más similares.
.SH OPCIONES
.TP
\fB\-\-index\fR \fICARPETA\fR
Carpeta que contiene las imágenes a indexar. Se procesan todos los archivos
con extensión: jpg, jpeg, png, gif, bmp, webp, tiff.
.TP
\fB\-\-search\fR \fIIMAGEN\fR
Imagen objetivo para buscar imágenes similares en el índice.
.TP
\fB\-i\fR, \fB\-\-indice\fR \fIINDICE.JSON\fR
Archivo de índice JSON generado previamente con \fB\-\-index\fR.
.TP
\fB\-o\fR, \fB\-\-output\fR \fISALIDA.JSON\fR
Archivo de salida JSON. Si no se especifica, usa \fBresultado.json\fR.
.TP
\fB\-\-threshold\fR \fIN\fR
Umbral mínimo de similitud (0\-100). Solo se muestran resultados con
similitud igual o superior a este valor. Default: 0 (todos).
.TP
\fB\-\-hash\fR \fITIPO\fR
Tipo de hash perceptual a usar para la comparación:
.RS
.IP \fBphash\fR 3
Perceptual Hash (default). Más robusto a compresiones.
.IP \fBahash\fR 3
Average Hash. Basado en promedio de píxeles.
.IP \fBdhash\fR 3
Difference Hash. Basado en diferencias entre píxeles.
.IP \fBwhash\fR 3
Wavelet Hash. Usa transformada wavelet.
.RE
.TP
\fB\-\-tamano\fR \fIN\fR
Tamaño para procesamiento binario (default: 32). Debe ser potencia de 2.
.SH EJEMPLOS
.TP
Indexar todas las imágenes de una carpeta:
.B
.RS
\fBimghash \-\-index /home/usuario/fotos \-o indice.json\fR
.RE
.TP
Buscar imágenes similares (todas):
.B
.RS
\fBimghash \-\-search objetivo.jpg \-i indice.json \-o resultados.json\fR
.RE
.TP
Buscar solo imágenes con más del 80% de similitud:
.B
.RS
\fBimghash \-\-search objetivo.jpg \-i indice.json \-\-threshold 80 \-o resultados.json\fR
.RE
.TP
Usar dhash en lugar de phash:
.B
.RS
\fBimghash \-\-search objetivo.jpg \-i indice.json \-\-hash dhash \-o resultados.json\fR
.RE
.SH FORMATO DEL ÍNDICE
El archivo JSON de índice contiene:
.RS
.IP \(bu 2
\fBfecha_generacion\fR: Fecha de creación del índice
.IP \(bu 2
\fBcarpeta_origen\fR: Ruta de la carpeta indexada
.IP \(bu 2
\fBimagenes\fR: Array de imágenes con:
.RS
.IP \(bu 2
\fBruta\fR: Ruta absoluta del archivo
.IP \(bu 2
\fBnombre\fR: Nombre del archivo
.IP \(bu 2
\fBhashes\fR: Objecto con phash, ahash, dhash, whash
.IP \(bu 2
\fBhash_binario\fR: Imagen procesada en base64 (blanco/negro 32x32)
.RE
.RE
.SH FORMATO DE RESULTADOS
El archivo JSON de resultados contiene:
.RS
.IP \(bu 2
\fBobjetivo\fR: Ruta de la imagen buscada
.IP \(bu 2
\fBhash_objetivo\fR: Hash de la imagen objetivo
.IP \(bu 2
\fBsimilares\fR: Array de imágenes similares ordenado por similitud:
.RS
.IP \(bu 2
\fBruta\fR: Ruta del archivo
.IP \(bu 2
\fBdistancia_hamming\fR: Diferencia entre hashes (0 = idéntico)
.IP \(bu 2
\fBsimilitud_pct\fR: Porcentaje de similitud (100 = idéntico)
.RE
.RE
.SH ALGORITMO
El hash perceptual (phash) funciona redimensionando la imagen a 32x32,
convirtiéndola a escala de grises, calculando una transformada DCT y
comparando con la media. Esto produce un hash que se mantiene similar
incluso cuando la imagen es comprimida, redimensionada o ligeramente
modificada.
.PP
La distancia Hamming cuenta los bits diferentes entre dos hashes.
Una distancia de 0\-4 bits generalmente indica imágenes muy similares
o idénticas. Distancias de 5\-10 bits indican相似 (posibles ediciones).
.SH AUTOR
Script creado para búsqueda de imágenes duplicadas/similares.
.SH VERTambién
.BR imagehash (3),
.BR pillow (3)


=============================================================================
SECCIÓN 3: EJEMPLOS DE USO
=============================================================================

# Instalación de dependencias
pip install imagehash

# Ejemplo 1: Indexar una carpeta de fotos
python3 imghash.py --index /home/usuario/Photos -o indice_fotos.json

# Ejemplo 2: Buscar duplicados de una imagen específica
python3 imghash.py --search /home/usuario/Photos/vacaciones.jpg --i indice_fotos.json -o duplicados.json

# Ejemplo 3: Buscar solo imágenes muy similares (>85%)
python3 imghash.py --search foto.jpg --i indice.json --threshold 85 -o similares.json

# Ejemplo 4: Usar un hash diferente (dhash)
python3 imghash.py --search foto.jpg --i indice.json --hash dhash -o resultados.json

# Ver resultados
cat duplicados.json | python3 -m json.tool


=============================================================================
SECCIÓN 4: EXPLICACIÓN DEL ALGORITMO
=============================================================================

PROBLEMA:
Cuando envías una imagen por WhatsApp (o cualquier messenger), la imagen se
comprime y puede cambiar su tamaño, formato o calidad. Esto significa que:
- El hash MD5/SHA será COMPLETAMENTE diferente
- Necesitamos un hash que sea "perceptual" (basado en cómo se ve la imagen)

SOLUCIÓN: Perceptual Hash (pHash)

El algoritmo phash funciona así:
1. Convertir la imagen a escala de grises
2. Redimensionar a un tamaño fijo (ej: 32x32)
3. Aplicar Transformada Discreta del Coseno (DCT)
4. Comparar cada coeficiente con la media
5. Generar un hash binario basado en si es mayor o menor que la media

Esto significa que dos imágenes visualmente similares tendrán hashes similares,
incluso si sus bytes son completamente diferentes.

DISTANCIA HAMMING:
Es el número de posiciones en las que los bits correspondientes son diferentes.
- Distancia 0 = misma imagen
- Distancia 1-4 = muy similar (compresión diferente)
- Distancia 5-10 = similar (ligeros cambios)
- Distancia >10 = diferente

Por ejemplo:
- Hash A: 11110000
- Hash B: 11110001
- Distancia Hamming: 1 (son muy similares)

TSNE:
Para comparar, calculamos similitud como:
similitud = (1 - distancia / longitud_total) * 100


=============================================================================
HISTORIAL DE SESIÓN
=============================================================================

Fecha: 7 de Marzo de 2026

Desarrollado para un usuario que necesitaba encontrar imágenes duplicadas
o similares que habían sido enviadas a través de WhatsApp, ya que la compresión
del messenger изменяет el hash tradicional.

Archivos creados:
- imghash.py (script principal)
- imghash.1 (página de manual)
- README.md (documentación)

El script ofrece:
- Indexación de carpetas de imágenes
- Múltiples tipos de hash (phash, ahash, dhash, whash)
- Salida en JSON
- Threshold configurable
- Búsqueda de similares en índice existente
'''
