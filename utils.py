import yt_dlp
import json


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
