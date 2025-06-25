# Stream Transcriber

Un proyecto para transcribir vídeos de YouTube a texto en tiempo real, admitiendo tanto streams en vivo como vídeos ya subidos a la plataforma.

## Descripción

Stream Transcriber es una herramienta que permite capturar streams de YouTube y transcribir su contenido de audio a texto de forma automática mientras el stream está en vivo. Este proyecto soporta dos modelos de transcripción:

1. **Whisper**: Procesa los datos en memoria RAM y es adecuado para transcripciones rápidas.
2. **WhisperX**: Utiliza archivos temporales y ofrece detección de hablantes. **(En desarrollo)**


## Características 

- Captura de streams de YouTube en vivo
- Transcripción automática de audio a texto
- Procesamiento en tiempo real
- Guardado de transcripciones para consulta posterior
- Soporte para modelos Whisper y WhisperX
- Posibilidad de diarización de hablantes (WhisperX)

## Requisitos

- Python 3.8 o superior (hasta 3.12 para compatibilidad con WhisperX)
- FFmpeg instalado en el sistema
- Conexión a internet

## Dependencias

Se encontrarán las siguientes dependencias en el archivo `requirements.txt`:

```plaintext
yt-dlp
openai-whisper
ffmpeg-python
whisperx
```

## Instalación

1. Clona este repositorio
   ```bash
   git clone https://github.com/your-username/Stream-transcriber.git
   cd Stream-transcriber
   ```

2. Instala las dependencias requeridas
   ```bash
   pip install -r requirements.txt
   ```

3. Asegúrate de tener FFmpeg instalado en tu sistema
   - Para Ubuntu/Debian: `sudo apt install ffmpeg`
   - Para macOS (con Homebrew): `brew install ffmpeg`
   - Para Windows: [Descargar FFmpeg](https://ffmpeg.org/download.html)

4. En caso de utilizar WhisperX.

 La instalación suele dar problemas, la propia pagina de [WhisperX](https://github.com/m-bain/whisperX) tiene un apartado de solucion de problemas que puedes consultar. 


 Si sigue dando problemas, una posible solucion para tarjetas NVIDIA en sistemas operativos Ubuntu/Debian es la siguiente: 

   - Se necesita tener instalado el paquete `nvidia-cuda-toolkit` para ello ejecuta:
   ```bash
      sudo apt update && sudo apt install -y nvidia-cuda-toolkit
   ```

   - Luego sigue la guía de instalación de cuDNN para tu sistema operativo. Puedes encontrar las instrucciones en el sitio oficial de [NVIDIA](https://developer.nvidia.com/cuda-downloads).

   - Finalmente, hay que ejecutar:
   ```bash
      # Añadir el repo de NVIDIA si no está
      sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub
      sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"

      # Actualizar e instalar cuDNN
      sudo apt update
      sudo apt install libcudnn8 libcudnn8-dev libcudnn8-samples
   ```

## Uso

Para ejecutar el transcriptor de whisper con los valores predeterminados solo es necesario la url del stream:

```bash
python transcriptor-whisper.py --url "https://www.youtube.com/watch?v=STREAM_ID"
```

Por otro lado, si deseas utilizar WhisperX, puedes ejecutar el siguiente comando:

```bash
python transcriptor-whisper.py --url "https://www.youtube.com/watch?v=STREAM_ID" --token "YOUR_HG_KEY" 
```


Los argumentos disponibles son:
- `--url`: URL del stream de YouTube a transcribir
- `--token`: Token de Hugging Face necesario para utilizar la diarización en WhisperX, para más información visita el repositorio de [WhisperX](https://github.com/m-bain/whisperX?tab=readme-ov-file#speaker-diarization)
- `--model`: Tamaño del modelo Whisper a utilizar (tiny, base, small, medium, large), predeterminado es `small`
- `--language`: Código de idioma para la transcripción (ej: es, en, fr), predeterminado se detecta automáticamente
- `--output`: Archivo de salida para guardar la transcripción, predeterminado es `transcripcion.txt`
- `--chunk-size`: Tamaño del fragmento de audio en segundos, predeterminado es `10`

### Terminación del programa

Para detener la transcripción en cualquier momento, simplemente presiona **Ctrl+C**. El programa finalizará de manera controlada, asegurándose de que todos los procesos terminen correctamente y que las transcripciones se guarden.

## Comentario sobre el proyecto
La implementación del modelo de Whisper es bastante sencilla, ya que se basa en la librería `openai-whisper` y no requiere de una configuración compleja. Además, el procesamiento se realiza en memoria RAM, lo que permite una transcripción rápida y eficiente. Se recomienda utilizar este script.

La implementación de WhisperX es más complicada debido a la necesidad de manejar archivos temporales y la detección de hablantes, lo que añade un nivel adicional de complejidad al proyecto. El rendimiento del modelo, o al menos de esta implementación, no es tan bueno como el de Whisper,dejando incluso bloques de audio sin procesar, por lo que se recomienda utilizarlo solo si se desea usar la diarización.

## Estado del proyecto

🚧 **En desarrollo** - Este proyecto acaba de iniciar y está en proceso de implementación. Aún no está listo para uso en producción.
