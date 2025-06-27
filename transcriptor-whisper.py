import whisper
import subprocess
import threading
import queue
import numpy as np
import argparse
from datetime import datetime
from utils import get_audio_stream_url, load_correct_words, corregir_texto, setup_logging

# Variable global para controlar la terminación ordenada
shutdown_event = threading.Event()

# Cola para comunicación entre hilos
audio_queue = queue.Queue()
transcription_queue = queue.Queue()
correction_queue = queue.Queue()

def stream_audio_from_youtube(youtube_url, chunk_size=10):
    """Captura el audio de YouTube y lo coloca en chunks en la cola."""
    
    # Obtener la URL del stream de audio
    try:
        stream_url = get_audio_stream_url(youtube_url)
    except Exception as e:
        logger.error(f"[Stream] Error obteniendo la URL del stream: {e}")
        shutdown_event.set()
        return
    
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
    process = None
    try:    
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        
        chunk_samples = 16000 * chunk_size  # Tamaño del chunk en segundos a 16kHz
        while not shutdown_event.is_set():
            chunk = process.stdout.read(chunk_samples * 2)  # 16-bit = 2 bytes por muestra
            if not chunk:
                audio_queue.put(None)
                logger.info("[Stream] Fin del stream normalmente.")
                break

            # Convertir a numpy array para procesamiento
            audio_data = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
            audio_queue.put(audio_data)
                            
    except Exception as e:
            logger.error(f"[Stream] Error capturando audio: {e}")
            shutdown_event.set()  # Señalar a otros hilos que deben terminar
    
    finally:
        if shutdown_event.is_set():
            logger.info("[Stream] Finalizando captura de audio por señal de cierre.")
                    
        if process:
            logger.info("[Stream] Cerrando proceso de audio.")
            try:
                process.terminate()
                process.wait(5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.error(f"[Stream] Error cerrando proceso: {e}")
        

def transcription_worker(model_size="small", language=None):
    """Procesa los chunks de audio y genera transcripciones."""
    model = whisper.load_model(model_size)
    while not shutdown_event.is_set(): # Hay datos en la cola pero se ha recibido una señal de cierre
        try:
            audio_data = audio_queue.get(timeout=1)
            if audio_data is None:
                transcription_queue.put((None, ""))
                logger.info("[Transcripción] Fin de la cola de audio.")
                break  # Terminar si se recibe None

            result = model.transcribe(audio_data, language=language)
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcription_queue.put((timestamp, result["text"]))
            
        except queue.Empty:
            # Si no hay datos pero no es shutdown, continuar esperando
            if not shutdown_event.is_set():
                continue
            else:
                break
        
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            shutdown_event.set()  
            break

    if shutdown_event.is_set():
        logger.info("[Transcripción] Finalizando por señal de cierre.")
    
  

def correct_transcriptions(input_file=None):
    """Corrige las transcripciones en la cola."""
    if input_file is None:
        datos_correccion = None
    else:
        datos_correccion = load_correct_words(input_file)

    while not shutdown_event.is_set():
        try:
            timestamp, text = transcription_queue.get(timeout=1)
            if timestamp is None:
                correction_queue.put((None, ""))
                logger.info(f"[Corrección] Corrección finalizada normalmente.")
                break  # Terminar si se recibe None
            
            if datos_correccion:
                # Usar la función optimizada de corrección
                corrected_text = corregir_texto(text.strip(), datos_correccion, umbral=0.7)
                correction_queue.put((timestamp, corrected_text))
            else:
                # Sin corrección, pasar el texto tal como está
                correction_queue.put((timestamp, text.strip()))
            
        except queue.Empty:
             # Si no hay datos pero no es shutdown, continuar esperando
            if not shutdown_event.is_set():
                continue
            else:
                break

        except Exception as e:
            logger.error(f"[Corrección] Error corrigiendo transcripción: {e}")
            shutdown_event.set()
            break

    if shutdown_event.is_set():        
        logger.info("[Corrección] Finalizando por señal de cierre.")

def output_worker(output_file="transcripcion.txt"):
    """Muestra las transcripciones a medida que están disponibles."""
    with open(output_file, "a", encoding="utf-8") as f:
        while not shutdown_event.is_set():
            try:
                timestamp, text = correction_queue.get(timeout=1)
                if timestamp is None:
                    logger.info(f"[Salida] Salida finalizada normalmente.")
                    break  # Terminar si se recibe None 
                
                if text.strip():
                    output = f"[{timestamp}]: {text}"
                    print(output)
                    f.write(output + "\n")
                    f.flush()
                
            except queue.Empty:
                 # Si no hay datos pero no es shutdown, continuar esperando
                if not shutdown_event.is_set():
                    continue
                else:
                    break

            except Exception as e:
                logger.error(f"[Salida] Error mostrando transcripción: {e}")
                shutdown_event.set()
                break

        if shutdown_event.is_set():
            logger.info("[Salida] Finalizando por señal de cierre.")

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

    # Iniciar hilo para corrección de transcripciones
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
    
    try:
        # Esperar a que terminen los hilos
        audio_thread.join()
        transcription_thread.join()
        correction_thread.join()
        output_thread.join()
        
        logger.info("[SISTEMA] Todos los hilos han terminado correctamente.")
        
    except KeyboardInterrupt:
        # Captura Ctrl+C para terminación ordenada de todos los hilos
        logger.info("[SISTEMA] Interrupción detectada en hilo principal.")
        shutdown_event.set()
        
    finally:
        # Asegurar que todos los hilos terminen
        if not shutdown_event.is_set():
            shutdown_event.set()
            
        # Dar tiempo a los hilos para terminar ordenadamente
        for thread in [audio_thread, transcription_thread, correction_thread, output_thread]:
            if thread.is_alive():
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning(f"[SISTEMA] Advertencia: El hilo {thread.name} no terminó en el tiempo esperado.")
                    raise RuntimeError(f"Hilo {thread.name} no terminó en el tiempo esperado.")
        
        # Confirmar cierre ordenado
        logger.info("[SISTEMA] Cierre ordenado completado.")

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
    parser.add_argument('--debug', action='store_true',
                        help='Activar modo debug')
    
    args = parser.parse_args()
    
    # Configurar logging
    logger = setup_logging(args.debug)
    
    logger.info("Iniciando transcripción del stream...")
    logger.info(f"URL: {args.url}")
    logger.info(f"Modelo: {args.model}")
    logger.info(f"Idioma: {args.language}")
    logger.info(f"Archivo de salida: {args.output}")
    logger.info(f"Tamaño del chunk: {args.chunk_size} segundos")
    logger.info(f"Archivo de palabras correctas: {args.correct_words if args.correct_words else 'No se utilizará corrección'}")
    print()
    
    
    transcribe_live_stream(args.url, args.model, args.language, args.output, args.chunk_size, args.correct_words)
