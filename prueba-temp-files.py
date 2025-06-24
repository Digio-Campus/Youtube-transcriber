import yt_dlp
import whisper
import tempfile
import os
import uuid
import threading
import queue
import argparse
import time

# Cola para comunicación entre hilos
audio_queue = queue.Queue()
result_queue = queue.Queue()

def extract_youtube_audio(youtube_url, chunk_size=10):
    """Extrae audio de YouTube en chunks y los pone en la cola."""
    
    # Opciones para yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        is_live = info.get('is_live', False)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            
            # Para streams en vivo, usamos un enfoque de descarga continua
            if is_live:
                print("Detectado stream en vivo, iniciando extracción continua...")
               
                stream_opts = ydl_opts.copy()
                stream_opts['external_downloader'] = 'ffmpeg' 
                stream_opts['external_downloader_args'] = ['-t', str(chunk_size)] 

                # En un stream en vivo, descargamos en chunks
                while True:
                    # Generar nombre único para este chunk
                    chunk_id = uuid.uuid4().hex
                    stream_opts['outtmpl'] = os.path.join(temp_dir, f'temp_stream_{chunk_id}')
                    
                    # Descargar el chunk de audio
                    with yt_dlp.YoutubeDL(stream_opts) as ydl_stream:                    
                        ydl_stream.download([youtube_url])

                    # Convertir el nombre del archivo descargado a WAV y ponerlo en la cola
                    filepath = os.path.join(temp_dir, f'temp_stream_{chunk_id}.wav')
                    audio_queue.put(filepath)

                    time.sleep(chunk_size/2)  # Esperar el tamaño del chunk antes de descargar el siguiente

            else:
                print("No es un stream en vivo, descargando video completo.")
                # Para videos normales, descargamos todo de una vez
                ydl_opts['outtmpl'] = os.path.join(temp_dir, 'complete_video')  # Nombre de archivo fijo
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_video:
                    ydl_video.download([youtube_url])
                    filepath = os.path.join(temp_dir, 'complete_video.wav')  # Referenciar el archivo directamente
                    audio_queue.put(filepath)
        
        except Exception as e:
            print(f"Error en extracción de audio: {e}")

        finally:    
            audio_queue.join()  # Esperar a que se procesen los archivos temporales
            print("Extracción de audio finalizada.")
            audio_queue.put(None)  # Señalizar fin de la extracción 
            

def transcribe_audio_chunks(model_size="small", language=None):
    """Transcribe los chunks de audio usando Whisper."""
    
    # Cargar modelo de Whisper
    print("Cargando modelo Whisper...")
    model = whisper.load_model("base")  # Puedes usar "small", "medium", "large" para mejor calidad
    
    while True:
        # Obtener archivo de audio de la cola
        audio_file = audio_queue.get()
        
        # None señaliza fin del stream
        if audio_file is None:
            audio_queue.task_done()
            break
            
        try:
            # Transcribir audio
            result = model.transcribe(audio_file) 

            # Verificar si el archivo es de stream y eliminarlo después de transcribir
            if(audio_file.startswith("temp_stream")):
                os.remove(audio_file) 
            
            # Añadir resultado a la cola de resultados
            result_queue.put(result["text"])
            
        except Exception as e:
            print(f"Error en transcripción: {e}")
        
        finally:
            audio_queue.task_done()

    
    # Señalizar fin de la transcripción
    result_queue.put(None)
    print("Transcripción completa.")


def output_worker(output_file="transcripcion.txt"):
    """Muestra las transcripciones a medida que están disponibles."""
    with open(output_file, "a", encoding="utf-8") as f:
        while True:
            try:
                result = result_queue.get()
                if result is None:
                    print("Redacción completa. Resultados guardados en 'transcripcion.txt'")
                    break

                if result.strip():
                    print(result)
                    f.write(result + "\n")
                    f.flush()

                # Procesar resultados
            except queue.Empty:
                print("[WARNING] No se recibieron transcripciones en 30 segundos, finalizando.")
                break
            except Exception as e:
                print(f"Error mostrando transcripción: {e}")
                continue
   

def transcribe_live_stream(youtube_url, model_size="small", language="es", output_file="transcripcion.txt", chunk_size=10):
    """Inicia los hilos para transcribir un stream en vivo.""" 
    # Iniciar hilo para capturar audio
    extractor_thread = threading.Thread(
        target=extract_youtube_audio, 
        args=(youtube_url,chunk_size)
    )
    extractor_thread.daemon = True
    extractor_thread.start()
    
    # Iniciar hilo para transcripción
    transcription_thread = threading.Thread(
        target=transcribe_audio_chunks,
        args=(model_size, language)
    )
    transcription_thread.daemon = True
    transcription_thread.start()
    
    # Iniciar hilo para mostrar resultados
    output_thread = threading.Thread(
        target=output_worker,
        args=(output_file,)
    )
    output_thread.daemon = True
    output_thread.start()
    
    # Esperar a que terminen los hilos
    extractor_thread.join()
    transcription_thread.join()
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
    
    args = parser.parse_args()
    
    print("Iniciando transcripción del stream...")
    print(f"URL: {args.url}")
    print(f"Modelo: {args.model}")
    print(f"Idioma: {args.language}")
    print(f"Archivo de salida: {args.output}")
    print(f"Tamaño del chunk: {args.chunk_size} segundos")

    transcribe_live_stream(args.url, args.model, args.language, args.output, args.chunk_size)
