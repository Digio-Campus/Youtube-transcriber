import yt_dlp
import json
import jellyfish
import re


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
    """Carga la lista de palabras correctas desde un archivo JSON."""
    correct_words = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Si el JSON tiene categorías, combinar todas las listas
        if isinstance(data, dict):
            for category in data.values():
                if isinstance(category, list):
                    correct_words.extend(category)
        # Si es una lista directa
        elif isinstance(data, list):
            correct_words = data
            
    except FileNotFoundError:
        print(f"Archivo {file_path} no encontrado. No se cargarán palabras correctas.")
    except json.JSONDecodeError:
        print(f"Error al leer el archivo JSON {file_path}.")
    except Exception as e:
        print(f"Error cargando palabras correctas: {e}")
    
    return correct_words

def crear_indice_fonetico(lista_palabras_correctas):
    """Crea un índice fonético para búsquedas más rápidas."""
    indice = {}
    for palabra in lista_palabras_correctas:
        codigo = jellyfish.metaphone(palabra)
        if codigo not in indice:
            indice[codigo] = []
        indice[codigo].append(palabra)
    return indice

def levinshtein_distance(palabra_incorrecta, palabras_correctas, umbral=0.8):
    """Calcula la distancia de Levenshtein entre una palabra incorrecta y una lista de palabras correctas."""
    mejor_coincidencia = None
    mejor_puntuacion = 0
    
    for palabra_correcta in palabras_correctas:
        similitud = 1 - (jellyfish.levenshtein_distance(palabra_incorrecta, palabra_correcta) / 
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

def corregir_texto(texto, lista_palabras_correctas, umbral=0.8):
    """Versión optimizada de corrección de texto."""
    # Crear índice fonético una sola vez
    indice_fonetico = crear_indice_fonetico(lista_palabras_correctas)
    
    # Convertir lista a set para búsquedas O(1)
    set_palabras_correctas = set(palabra.lower() for palabra in lista_palabras_correctas)
    
    palabras = re.findall(r'\b\w+\b', texto)
    texto_corregido = texto
    
    for palabra in palabras:
        
        if palabra.lower() in set_palabras_correctas:
            continue # La palabra ya es correcta
        
        if len(palabra) < 3 or palabra.isdigit():
            continue # Ignorar palabras muy cortas o números
        
        palabra_corregida = corregir_palabra(palabra, indice_fonetico, lista_palabras_correctas, umbral)
        if palabra_corregida != palabra:
            # Reemplazar la palabra incorrecta por la corregida en el texto
            texto_corregido = re.sub(r'\b' + re.escape(palabra) + r'\b', 
                                   palabra_corregida + ("corregida"), texto_corregido)
    
    return texto_corregido