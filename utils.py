import yt_dlp
import json
import jellyfish
import re
from unidecode import unidecode   

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
    except json.JSONDecodeError:
        print(f"Error al leer el archivo JSON {file_path}.")
    except Exception as e:
        print(f"Error cargando palabras correctas: {e}")
    
    return correct_words

def crear_indice_fonetico(set_palabras_correctas):
    """Crea un índice fonético para búsquedas más rápidas."""
    indice = {}
    for palabra in set_palabras_correctas:
        codigo = jellyfish.metaphone(palabra)
        if codigo not in indice:
            indice[codigo] = []
        indice[codigo].append(palabra)
    return indice

def levinshtein_distance(palabra_incorrecta, set_palabras_correctas, umbral=0.8):
    """Calcula la distancia de Levenshtein entre una palabra incorrecta y una lista de palabras correctas."""
    mejor_coincidencia = None
    mejor_puntuacion = 0
    # Normalizar para comparación (minúsculas + sin tildes)
    palabra_incorrecta_norm = normalizar_palabra(palabra_incorrecta)
    
    for palabra_correcta in set_palabras_correctas:
        palabra_correcta_norm = normalizar_palabra(palabra_correcta)
        similitud = 1 - (jellyfish.levenshtein_distance(palabra_incorrecta_norm, palabra_correcta_norm) / 
                         max(len(palabra_incorrecta), len(palabra_correcta)))
        
        if similitud > mejor_puntuacion and similitud > umbral:
            mejor_puntuacion = similitud
            mejor_coincidencia = palabra_correcta
    
    return mejor_coincidencia if mejor_coincidencia else palabra_incorrecta

def corregir_palabra(palabra_incorrecta, indice_fonetico, lista_palabras_correctas, umbral=0.8):
    """Versión optimizada de corrección de palabras usando índice fonético."""
    codigo_fonetico = jellyfish.metaphone(palabra_incorrecta)
    
    # Búsqueda fonética O(1) - muy rápida
    if codigo_fonetico in indice_fonetico:
        candidatos_foneticos = indice_fonetico[codigo_fonetico]
        
        # Si solo hay un candidato fonético, devolverlo
        if len(candidatos_foneticos) == 1:
            return candidatos_foneticos[0]
        
        # Si hay múltiples candidatos fonéticos, usar Levenshtein para elegir el mejor
        return levinshtein_distance(palabra_incorrecta, candidatos_foneticos, umbral)
    
    # Si no hay coincidencia fonética, buscar por similitud Levenshtein
    return levinshtein_distance(palabra_incorrecta, lista_palabras_correctas, umbral)

def corregir_texto(texto, set_palabras_correctas, umbral=0.8, indice_fonetico=None):
    """Versión optimizada de corrección de texto."""
    # Crear índice fonético si no se proporciona
    if indice_fonetico is None:
        indice_fonetico = crear_indice_fonetico(set_palabras_correctas)
    
    palabras = re.findall(r'\b\w+\b', texto)
    texto_corregido = texto
    
    for palabra in palabras:

        if palabra in set_palabras_correctas:
            continue # La palabra ya es correcta

        if palabra.isdigit() or len(palabra) < 3:
            continue # Ignorar palabras muy cortas o números

        # Usar palabra normalizada como clave del cache
        cache_key = normalizar_palabra(palabra)
        cache = False
        if cache_key in _cache_correcciones:
            palabra_corregida = _cache_correcciones[cache_key]
            cache = True
        else:
            palabra_corregida = corregir_palabra(palabra, indice_fonetico, set_palabras_correctas, umbral)
        
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
