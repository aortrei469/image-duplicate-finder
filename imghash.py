#!/usr/bin/env python3
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


def indexar_carpeta(carpeta, tamano=32, indice_existente=None, actualizar=False):
    carpeta_path = Path(carpeta)
    if not carpeta_path.exists():
        print(f"Error: La carpeta '{carpeta}' no existe", file=sys.stderr)
        sys.exit(1)
    
    extensiones = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    
    rutas_indexadas = set()
    if indice_existente and not actualizar:
        for img in indice_existente.get('imagenes', []):
            if 'ruta' in img:
                rutas_indexadas.add(img['ruta'])
        print(f"Índice existente: {len(rutas_indexadas)} imágenes ya indexadas")
    
    archivos = list(carpeta_path.rglob('*'))
    archivos_para_procesar = [a for a in archivos if a.suffix.lower() in extensiones]
    
    if indice_existente and not actualizar:
        archivos_para_procesar = [a for a in archivos_para_procesar if str(a.absolute()) not in rutas_indexadas]
    
    total = len(archivos_para_procesar)
    print(f"Indexando {total} imágenes nuevas de '{carpeta}'...")
    
    imagenes_nuevas = []
    
    for i, archivo in enumerate(archivos_para_procesar):
        try:
            hashes = calcular_hashes(archivo)
            img_binaria = procesar_imagen(archivo, tamano)
            bytes_img = img_binaria.tobytes()
            hash_binario = base64.b64encode(bytes_img).decode('utf-8')
            
            imagenes_nuevas.append({
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
    
    print(f"  Total nuevas indexadas: {len(imagenes_nuevas)}")
    
    if indice_existente and not actualizar:
        todas_imagenes = indice_existente.get('imagenes', []) + imagenes_nuevas
        return {
            'fecha_generacion': datetime.now().isoformat(),
            'carpeta_origen': indice_existente.get('carpeta_origen', str(carpeta_path.absolute())),
            'tamano_procesamiento': tamano,
            'total_imagenes': len(todas_imagenes),
            'imagenes': todas_imagenes
        }
    
    return {
        'fecha_generacion': datetime.now().isoformat(),
        'carpeta_origen': str(carpeta_path.absolute()),
        'tamano_procesamiento': tamano,
        'total_imagenes': len(imagenes_nuevas),
        'imagenes': imagenes_nuevas
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


def generar_hash_index(indice, hash_type='phash'):
    hashes_ordenados = []
    for i, img in enumerate(indice.get('imagenes', [])):
        h = img.get('hashes', {}).get(hash_type, '')
        if h:
            hashes_ordenados.append({'hash': h, 'indice': i})
    
    hashes_ordenados.sort(key=lambda x: x['hash'])
    
    return {
        'tipo_hash': hash_type,
        'fecha_generacion': datetime.now().isoformat(),
        'total': len(hashes_ordenados),
        'hashes': hashes_ordenados
    }


def guardar_hash_index(hash_index, indice_path):
    base = indice_path.rsplit('.json', 1)[0] if indice_path.endswith('.json') else indice_path
    hash_index_path = f"{base}_hash.json"
    guardar_indice(hash_index, hash_index_path)
    return hash_index_path


def cargar_hash_index(indice_path):
    base = indice_path.rsplit('.json', 1)[0] if indice_path.endswith('.json') else indice_path
    hash_index_path = f"{base}_hash.json"
    return cargar_indice(hash_index_path)


def distancia_hamming_entre(h1, h2):
    return distancia_hamming(h1, h2)


def encontrar_duplicados(indice, hash_index=None, threshold=85, hash_type='phash'):
    if hash_index and hash_index.get('tipo_hash') == hash_type:
        hashes_ordenados = hash_index.get('hashes', [])
    else:
        hashes_ordenados = generar_hash_index(indice, hash_type).get('hashes', [])
    
    if not hashes_ordenados:
        print("No hay hashes para comparar", file=sys.stderr)
        return {'grupos': [], 'estadisticas': {'total': 0, 'grupos': 0}}
    
    longitud_hash = len(hashes_ordenados[0]['hash'])
    max_dist = int((100 - threshold) / 100 * longitud_hash)
    if max_dist < 1:
        max_dist = 1
    
    imagenes = indice.get('imagenes', [])
    grupos = []
    grupo_actual = []
    
    for i, item in enumerate(hashes_ordenados):
        if not grupo_actual:
            grupo_actual = [item]
        else:
            item_anterior = grupo_actual[-1]
            dist = distancia_hamming(item_anterior['hash'], item['hash'])
            
            if dist <= max_dist:
                grupo_actual.append(item)
            else:
                if len(grupo_actual) > 1:
                    grupos.append(grupo_actual)
                grupo_actual = [item]
    
    if len(grupo_actual) > 1:
        grupos.append(grupo_actual)
    
    grupos_formateados = []
    for gid, grupo in enumerate(grupos, 1):
        refs = []
        ref_hash = grupo[0]['hash']
        for item in grupo:
            img = imagenes[item['indice']]
            dist = distancia_hamming(ref_hash, item['hash'])
            similitud = calcular_similitud(ref_hash, item['hash'])
            refs.append({
                'ruta': img.get('ruta', ''),
                'nombre': img.get('nombre', ''),
                'distancia_hamming': dist,
                'similitud_pct': similitud
            })
        grupos_formateados.append({
            'id_grupo': gid,
            'tamano': len(grupo),
            'imagenes': refs
        })
    
    grupos_formateados.sort(key=lambda x: -x['tamano'])
    
    total_dup = sum(g['tamano'] for g in grupos_formateados)
    
    return {
        'indice_utilizado': 'hash_index' if hash_index else 'indice_json',
        'tipo_hash': hash_type,
        'threshold': threshold,
        'distancia_maxima': max_dist,
        'grupos_similares': grupos_formateados,
        'estadisticas': {
            'total_imagenes': len(imagenes),
            'total_grupos': len(grupos_formateados),
            'imagenes_en_grupos': total_dup
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='Hash de imágenes para encontrar duplicados/similares'
    )
    parser.add_argument('--index', metavar='CARPETA', 
                        help='Carpeta a indexar')
    parser.add_argument('--update', action='store_true',
                        help='Reindexar todo (ignora índice existente)')
    parser.add_argument('--build-hash-index', action='store_true',
                        help='Generar índice de hashes separado (más rápido para búsquedas)')
    parser.add_argument('--find-dups', action='store_true',
                        help='Encontrar duplicados dentro del índice')
    parser.add_argument('--search', metavar='IMAGEN',
                        help='Buscar imagen similar en el índice')
    parser.add_argument('--i', '--indice', dest='indice', metavar='INDICE.JSON',
                        help='Fichero de índice (JSON)')
    parser.add_argument('-o', '--output', metavar='SALIDA.JSON',
                        help='Fichero de salida (JSON)')
    parser.add_argument('--threshold', type=int, default=0,
                        help='Umbral mínimo de similitud (0-100). Para --find-dups default: 85')
    parser.add_argument('--hash', dest='hash_type', 
                        choices=['phash', 'ahash', 'dhash', 'whash'], 
                        default='phash',
                        help='Tipo de hash a usar para comparación')
    parser.add_argument('--tamano', type=int, default=32,
                        help='Tamaño para procesamiento binario (default: 32)')
    
    args = parser.parse_args()
    
    output_file = args.output or 'resultado.json'
    
    if args.index:
        indice_existente = None
        if args.indice and not args.update:
            indice_existente = cargar_indice(args.indice)
            if indice_existente:
                output_file = args.indice
            elif not indice_existente and args.indice:
                print(f"Advertencia: No se pudo cargar índice '{args.indice}', creando nuevo", file=sys.stderr)
        
        indice = indexar_carpeta(args.index, args.tamano, indice_existente, args.update)
        guardar_indice(indice, output_file)
        print(f"Índice guardado en: {output_file}")
        print(f"Total imágenes en índice: {indice.get('total_imagenes', 0)}")
        
        if args.build_hash_index:
            hash_index = generar_hash_index(indice, args.hash_type)
            hash_path = guardar_hash_index(hash_index, output_file)
            print(f"Índice de hashes guardado en: {hash_path}")
        
    elif args.find_dups and args.indice:
        indice = cargar_indice(args.indice)
        if not indice:
            print(f"Error: No se pudo cargar el índice '{args.indice}'", file=sys.stderr)
            sys.exit(1)
        
        threshold = args.threshold if args.threshold > 0 else 85
        hash_index = cargar_hash_index(args.indice)
        
        if hash_index:
            print(f"Usando índice de hashes: {args.indice.rsplit('.json', 1)[0]}_hash.json")
        
        resultados = encontrar_duplicados(indice, hash_index, threshold, args.hash_type)
        guardar_indice(resultados, output_file)
        print(f"Encontrados {resultados['estadisticas']['total_grupos']} grupos de imágenes similares")
        print(f"Total imágenes en grupos: {resultados['estadisticas']['imagenes_en_grupos']}")
        print(f"Resultados guardados en: {output_file}")
        
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
        print("  # Indexar carpeta")
        print("  python imghash.py --index /fotos/ -o indice.json")
        print("")
        print("  # Indexar con índice de hashes (más rápido)")
        print("  python imghash.py --index /fotos/ -o indice.json --build-hash-index")
        print("")
        print("  # Indexación incremental")
        print("  python imghash.py --index /mas_fotos/ --indice indice.json -o indice.json")
        print("")
        print("  # Encontrar duplicados (rápido con índice de hashes)")
        print("  python imghash.py --find-dups indice.json -o duplicados.json")
        print("  python imghash.py --find-dups indice.json --threshold 90 -o dup90.json")
        print("")
        print("  # Buscar imagen específica")
        print("  python imghash.py --search foto.jpg --indice indice.json -o resultados.json")
        print("  python imghash.py --search foto.jpg --indice indice.json --threshold 80 -o resultados.json")


if __name__ == '__main__':
    main()
