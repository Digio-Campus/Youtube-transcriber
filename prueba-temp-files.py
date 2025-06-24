import yt_dlp
import whisper
import tempfile
import os
import uuid
import threading
import queue

# Cola para comunicación entre hilos
audio_queue = queue.Queue()
result_queue = queue.Queue()

def extract_youtube_audio(youtube_url, chunk_duration=10):
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
                stream_opts['external_downloader_args'] = ['-t', str(chunk_duration)] 

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
            

def transcribe_audio_chunks():
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
            print(f"Transcribiendo chunk de audio...")
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

def main(youtube_url):
    # Iniciar hilo para extracción de audio
    extractor_thread = threading.Thread(
        target=extract_youtube_audio, 
        args=(youtube_url,)
    )
    extractor_thread.daemon = True
    extractor_thread.start()
    
    # Iniciar hilo para transcripción
    transcription_thread = threading.Thread(
        target=transcribe_audio_chunks
    )
    transcription_thread.daemon = True
    transcription_thread.start()
    
    # Procesar resultados
    with open("transcripcion.txt", "w", encoding="utf-8") as f:
        while True:
            result = result_queue.get()
            
            # None señaliza fin del procesamiento
            if result is None:
                break
                
            print(result)
            f.write(result + "\n")
            f.flush()


    print("Redacción completa. Resultados guardados en 'transcripcion.txt'")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python script.py URL_DE_YOUTUBE")
        sys.exit(1)
        
    youtube_url = sys.argv[1]
    main(youtube_url)