import yt_dlp
import whisper
import subprocess
import threading
import queue
import numpy as np
from datetime import datetime

# Cola para comunicación entre hilos
audio_queue = queue.Queue()
transcription_queue = queue.Queue()

def get_audio_stream_url(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']
    
def stream_audio_from_youtube(youtube_url):
    """Captura el audio de YouTube y lo coloca en chunks en la cola."""
    
    # Obtener la URL del stream de audio
    stream_url = get_audio_stream_url(youtube_url)
    
    # Usar FFmpeg para procesar el stream en tiempo real
    cmd = [
        'ffmpeg', 
        '-loglevel', 'quiet',  # Silenciar la salida de FFmpeg
        '-i', stream_url, 
        '-vn',  # Sin video
        '-acodec', 'pcm_s16le',  # Audio en formato PCM de 16 bits
        '-f', 'wav',
        '-ar', '16000',
        '-ac', '1',
        '-'
    ]
        
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        
    chunk_size = 16000 * 10  # 10 segundos de audio a 16kHz
    while True:
        try:
            chunk = process.stdout.read(chunk_size * 2)  # 16-bit = 2 bytes por muestra
            if not chunk:
                break
                    
            # Convertir a numpy array para procesamiento
            audio_data = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
            audio_queue.put(audio_data)
                
        except Exception as e:
            print(f"Error capturando audio: {e}")
            break
                
    process.terminate()

def transcription_worker(model_size="small", language="es"):
    """Procesa los chunks de audio y genera transcripciones."""
    model = whisper.load_model(model_size)
    while True:
        try:
            audio_data = audio_queue.get(timeout=60)
            result = model.transcribe(audio_data, language=language)
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcription_queue.put((timestamp, result["text"]))
            
        except queue.Empty:
            print("No se recibió audio en 60 segundos, finalizando...")
            break
        except Exception as e:
            print(f"Error en transcripción: {e}")
            
def output_worker():
    """Muestra las transcripciones a medida que están disponibles."""
    with open("transcripcion.txt", "a", encoding="utf-8") as f:
        while True:
            try:
                timestamp, text = transcription_queue.get(timeout=60)
                output = f"[{timestamp}]: {text}"
                print(output)
                f.write(output + "\n")
                f.flush()
                
            except queue.Empty:
                print("No se recibieron transcripciones en 60 segundos, finalizando...")
                break
            except Exception as e:
                print(f"Error mostrando transcripción: {e}")

def transcribe_live_stream(youtube_url, model_size="small",language="es"):
    """Inicia los hilos para transcribir un stream en vivo."""
    # Iniciar hilo para capturar audio
    audio_thread = threading.Thread(
        target=stream_audio_from_youtube, 
        args=(youtube_url,)
    )
    audio_thread.daemon = True
    audio_thread.start()
    
    # Iniciar hilo para transcripción
    transcription_thread = threading.Thread(
        target=transcription_worker,
        args=(model_size, language)
    )
    transcription_thread.daemon = True
    transcription_thread.start()
    
    # Iniciar hilo para mostrar resultados
    output_thread = threading.Thread(
        target=output_worker,
    )
    output_thread.daemon = True
    output_thread.start()
    
    # Esperar a que terminen los hilos
    audio_thread.join()
    transcription_thread.join()
    output_thread.join()

if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=qlpsvA6L7iA"
    transcribe_live_stream(youtube_url)