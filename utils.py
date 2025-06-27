import yt_dlp
import json
import jellyfish
import re
from unidecode import unidecode   
import difflib

# Cache global para correcciones ya realizadas
_cache_correcciones = {}

def get_audio_stream_url(youtube_url):
    """Obtiene la URL del stream de audio de YouTube."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']


def load_correct_words(file_path="palabras_correctas.json"):
    """Carga un set de palabras correctas desde un archivo JSON."""
    correct_words = set()  # Usar un set para evitar duplicados 
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Si el JSON tiene categorías, combinar todas las listas
        if isinstance(data, dict):
            for categoria, palabras in data.items():
                if isinstance(palabras, list):
                    correct_words.update(palabras)
        # Si el JSON es una lista directa de palabras    
        elif isinstance(data, list):
            correct_words.update(data)
            
    except FileNotFoundError:
        print(f"Archivo {file_path} no encontrado. No se cargarán palabras correctas.")
        return None
    
    except json.JSONDecodeError:
        print(f"Error al leer el archivo JSON {file_path}.")
        return None
    
    except Exception as e:
        print(f"Error cargando palabras correctas: {e}")
        return None
    
    return crear_datos_precalculados(correct_words)

def crear_indice_fonetico(set_palabras_correctas):
    """Crea un índice fonético para búsquedas más rápidas."""
    indice = {}
    for palabra in set_palabras_correctas:
        codigo = jellyfish.metaphone(palabra)
        if codigo not in indice:
            indice[codigo] = []
        indice[codigo].append(palabra)
    return indice

def crear_listas_palabras_correctas(set_palabras_correctas):
    # Pre-calcular listas normalizadas para difflib
    palabras_correctas_list = list(set_palabras_correctas)
    palabras_norm = [normalizar_palabra(p) for p in palabras_correctas_list]
    return (palabras_correctas_list, palabras_norm)

def crear_datos_precalculados(set_palabras_correctas):
    """Crea un objeto de datos pre-calculados para corrección de palabras."""
    return {
        'set_palabras_correctas': set_palabras_correctas,
        'indice_fonetico': crear_indice_fonetico(set_palabras_correctas),
        'listas_palabras_correctas': crear_listas_palabras_correctas(set_palabras_correctas)
    }

def levinshtein_distance(palabra_incorrecta, listas_palabras, umbral=0.8):
    """Encuentra la mejor coincidencia usando difflib - más eficiente y preciso."""
    palabra_incorrecta_norm = normalizar_palabra(palabra_incorrecta)
    
    # Desempaquetar las listas pre-calculadas
    palabras_correctas_list, palabras_norm = listas_palabras
    
    # difflib.get_close_matches es MÁS EFICIENTE que un bucle manual
    coincidencias = difflib.get_close_matches(
        palabra_incorrecta_norm, 
        palabras_norm, 
        n=1,  # Solo la mejor coincidencia
        cutoff=umbral
    )
    
    if coincidencias:
        # Encontrar la palabra original correspondiente
        idx = palabras_norm.index(coincidencias[0])
        return palabras_correctas_list[idx]
    
    return palabra_incorrecta

def corregir_palabra(palabra_incorrecta, indice_fonetico, listas_palabras_correctas, umbral=0.8):
    """Versión optimizada de corrección de palabras usando índice fonético."""
    codigo_fonetico = jellyfish.metaphone(palabra_incorrecta)
    
    # Búsqueda fonética O(1) - muy rápida
    if codigo_fonetico in indice_fonetico:
        candidatos_foneticos = indice_fonetico[codigo_fonetico]
        
        # Si solo hay un candidato fonético, devolverlo
        if len(candidatos_foneticos) == 1:
            return candidatos_foneticos[0]
        
        # Si hay múltiples candidatos fonéticos, usar Levenshtein para elegir el mejor
        candidatos_foneticos_norm = [normalizar_palabra(p) for p in candidatos_foneticos]
        candidatos_foneticos = (candidatos_foneticos, candidatos_foneticos_norm)
        return levinshtein_distance(palabra_incorrecta, candidatos_foneticos, umbral)
    
    # Si no hay coincidencia fonética, buscar por similitud Levenshtein
    return levinshtein_distance(palabra_incorrecta, listas_palabras_correctas, umbral)

def corregir_texto(texto, datos_correccion, umbral=0.8):
    """Versión optimizada de corrección de texto."""
    # Desempaquetar los datos pre-calculados
    set_palabras_correctas = datos_correccion['set_palabras_correctas']
    indice_fonetico = datos_correccion['indice_fonetico']
    listas_palabras_correctas = datos_correccion['listas_palabras_correctas']

    # Usar regex para encontrar palabras
    palabras = re.findall(r'\b\w+\b', texto)
    texto_corregido = texto
    
    # Iterar sobre las palabras encontradas
    for palabra in palabras:

        # Usar set para ignorar palabras ya correctas
        if palabra in set_palabras_correctas:
            continue 

        # Ignorar palabras muy cortas o números
        if palabra.isdigit() or len(palabra) < 3:
            continue 

        # Usar palabra normalizada como clave del cache
        cache_key = normalizar_palabra(palabra)
        cache = False
        if cache_key in _cache_correcciones:
            palabra_corregida = _cache_correcciones[cache_key]
            cache = True
        else:
            palabra_corregida = corregir_palabra(palabra, indice_fonetico, listas_palabras_correctas, umbral)

        if palabra_corregida != palabra:
            if not cache:
                # Guardar en cache usando palabra normalizada como clave
                _cache_correcciones[cache_key] = palabra_corregida
            
            # Reemplazar la palabra incorrecta por la corregida en el texto
            texto_corregido = re.sub(r'\b' + re.escape(palabra) + r'\b', 
                                   palabra_corregida + (" (corregida)"), texto_corregido)
    
    return texto_corregido

def normalizar_palabra(texto):
    """Normaliza una palabra: convierte a minúsculas y quita tildes."""
    return unidecode(texto.lower())
