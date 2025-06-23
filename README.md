# Stream Transcriber

Un proyecto para transcribir streams de YouTube a texto en tiempo real.

## Descripción

Stream Transcriber es una herramienta que permite capturar streams de YouTube y transcribir su contenido de audio a texto de forma automática mientras el stream está en vivo. Este proyecto está actualmente en fase inicial de desarrollo.

## Características (previstas)

- Captura de streams de YouTube en vivo
- Transcripción automática de audio a texto
- Procesamiento en tiempo real
- Guardado de transcripciones para consulta posterior

## Requisitos

- Python 3.8 o superior
- FFmpeg instalado en el sistema
- Conexión a internet

## Dependencias

Se encontrarán las siguientes dependencias en el archivo `requirements.txt`:

```plaintext
yt-dlp
openai-whisper
ffmpeg-python
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

## Uso

Para ejecutar el transcriptor con los valores predeterminados solo es necesario la url del stream:

```bash
python main.py --url "https://www.youtube.com/watch?v=STREAM_ID"
```
Si deseas mayor control cueanta con las siguientes opciones:

```bash
python main.py --url "https://www.youtube.com/watch?v=STREAM_ID" --model "base" --language "es" --output "transcripcion.txt" --chunk-size 10
```   

Opciones disponibles:
- `--url`: URL del stream de YouTube a transcribir
- `--model`: Tamaño del modelo Whisper a utilizar (tiny, base, small, medium, large), predeterminado es `small`
- `--language`: Código de idioma para la transcripción (ej: es, en, fr), predeterminado detecta automáticamente
- `--output`: Archivo de salida para guardar la transcripción, predeterminado es `transcripcion.txt`
- `--chunk-size`: Tamaño del fragmento de audio en segundos, predeterminado es `10`

### Terminación del programa

Para detener la transcripción en cualquier momento, simplemente presiona **Ctrl+C**. El programa finalizará de manera controlada, asegurándose de que todos los procesos terminen correctamente y que las transcripciones se guarden.

## Estado del proyecto

🚧 **En desarrollo** - Este proyecto acaba de iniciar y está en proceso de implementación. Aún no está listo para uso en producción.
