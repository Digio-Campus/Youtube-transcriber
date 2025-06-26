import whisper
import subprocess
import threading
import queue
import numpy as np
import argparse
from datetime import datetime
import signal
import sys
from utils import get_audio_stream_url, load_correct_words, corregir_texto, crear_indice_fonetico

# Manejo de interrupciones manual
# Permite cerrar el script con Ctrl+C sin dejar procesos colgando
def signal_handler(sig, frame):
    print('Interrupción manual detectada. Cerrando...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


# Cola para comunicación entre hilos
audio_queue = queue.Queue()
transcription_queue = queue.Queue()
correction_queue = queue.Queue()

def stream_audio_from_youtube(youtube_url, chunk_size=10):
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
    try:    
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        
        chunk_samples = 16000 * chunk_size  # Tamaño del chunk en segundos a 16kHz
        while True:
            chunk = process.stdout.read(chunk_samples * 2)  # 16-bit = 2 bytes por muestra
            if not chunk:
                print("[Stream] Fin del stream o error al leer audio.")
                break

            # Convertir a numpy array para procesamiento
            audio_data = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
            audio_queue.put(audio_data)
                            
    except Exception as e:
            print(f"Error capturando audio: {e}")
    
    finally:
        print("[Stream] Cerrando proceso de audio.")
        audio_queue.put(None)
        try:
            process.terminate()
            process.wait(5)
        except subprocess.TimeoutExpired:
            process.kill()
        

def transcription_worker(model_size="small", language=None):
    """Procesa los chunks de audio y genera transcripciones."""
    model = whisper.load_model(model_size)
    while True:
        try:
            audio_data = audio_queue.get(timeout=30)
            if audio_data is None:
                print("[Reporducción] Fin de la cola de audio. ")
                break  # Terminar si se recibe None

            result = model.transcribe(audio_data, language=language)
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcription_queue.put((timestamp, result["text"]))
            
        except queue.Empty:
            print("[WARNING] No se recibió audio en 30 segundos, finalizando.")
            break
        except Exception as e:
            print(f"Error en transcripción: {e}")
            continue
    transcription_queue.put((None, "Transcripción finalizada."))

def correct_transcriptions(input_file=None):
    """Corrige las transcripciones en la cola."""
    if input_file is None:
        correct_words = None
    else:
        correct_words = load_correct_words(input_file)
        indice_fonetico = crear_indice_fonetico(correct_words)

    while True:
        try:
            timestamp, text = transcription_queue.get(timeout=30)
            if timestamp is None:
                print(f"[Transcripción] {text}")
                break  # Terminar si se recibe None
            
            if correct_words and len(correct_words) > 0:
                # Usar la función optimizada de corrección
                corrected_text = corregir_texto(text.strip(), correct_words, umbral=0.7, indice_fonetico=indice_fonetico)
                correction_queue.put((timestamp, corrected_text))
            else:
                # Sin corrección, pasar el texto tal como está
                correction_queue.put((timestamp, text.strip()))
            
        except queue.Empty:
            print("[WARNING] No se recibieron transcripciones en 30 segundos, finalizando.")
            break
        except Exception as e:
            print(f"Error corrigiendo transcripción: {e}")
            continue
    correction_queue.put((None, "Corrección finalizada."))


def output_worker(output_file="transcripcion.txt"):
    """Muestra las transcripciones a medida que están disponibles."""
    with open(output_file, "a", encoding="utf-8") as f:
        while True:
            try:
                timestamp, text = correction_queue.get(timeout=30)
                if timestamp is None:
                    print(f"[Correción] {text}")
                    break  # Terminar si se recibe None 
                
                if text.strip():
                    output = f"[{timestamp}]: {text}"
                    print(output)
                    f.write(output + "\n")
                    f.flush()
                
            except queue.Empty:
                print("[WARNING] No se recibieron transcripciones corregidas en 30 segundos, finalizando.")
                break
            except Exception as e:
                print(f"Error mostrando transcripción: {e}")
                continue

def transcribe_live_stream(youtube_url, model_size="small", language="es", output_file="transcripcion.txt", 
                           chunk_size=10, correct_words=None):
    """Inicia los hilos para transcribir un stream en vivo."""
    # Iniciar hilo para capturar audio
    audio_thread = threading.Thread(
        target=stream_audio_from_youtube, 
        args=(youtube_url, chunk_size)
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

    #Iniciar hilo para corrección de transcripciones
    correction_thread = threading.Thread(
        target=correct_transcriptions,
        args=(correct_words,)
    )
    correction_thread.daemon = True
    correction_thread.start()
    
    # Iniciar hilo para mostrar resultados
    output_thread = threading.Thread(
        target=output_worker,
        args=(output_file,)
    )
    output_thread.daemon = True
    output_thread.start()
    
    # Esperar a que terminen los hilos
    audio_thread.join()
    transcription_thread.join()
    correction_thread.join()
    output_thread.join()

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Transcribe YouTube live streams en tiempo real.')
    parser.add_argument('--url', type=str, required=True,
                        help='URL del stream de YouTube a transcribir')
    parser.add_argument('--model', type=str, default="small", choices=["tiny", "base", "small", "medium", "large"],
                        help='Tamaño del modelo de Whisper a utilizar')
    parser.add_argument('--language', type=str, default=None,
                        help='Código de idioma para la transcripción (ej: es, en, fr)')
    parser.add_argument('--output', type=str, default="transcripcion.txt",
                        help='Archivo de salida para guardar la transcripción')
    parser.add_argument('--chunk-size', type=int, default=10, 
                        help='Tamaño del fragmento de audio en segundos')
    parser.add_argument('--correct-words', type=str, default=None,
                        help='Archivo JSON con palabras correctas para corrección de transcripciones')
    
    args = parser.parse_args()
    
    print("Iniciando transcripción del stream...")
    print(f"URL: {args.url}")
    print(f"Modelo: {args.model}")
    print(f"Idioma: {args.language}")
    print(f"Archivo de salida: {args.output}")
    print(f"Tamaño del chunk: {args.chunk_size} segundos")
    print(f"Archivo de palabras correctas: {args.correct_words if args.correct_words else 'No se utilizará corrección'}")
    print()
    
    
    transcribe_live_stream(args.url, args.model, args.language, args.output, args.chunk_size, args.correct_words)
