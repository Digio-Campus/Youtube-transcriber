# Stream Transcriber

Un proyecto para transcribir vídeos de YouTube a texto en tiempo real, admitiendo tanto streams en vivo como vídeos ya subidos a la plataforma.

## Descripción

Stream Transcriber es una herramienta que permite capturar streams de YouTube y transcribir su contenido de audio a texto de forma automática mientras el stream está en vivo. Este proyecto soporta dos modelos de transcripción:

1. **Whisper**: Procesa los datos en memoria RAM y es adecuado para transcripciones rápidas.
2. **WhisperX**: Utiliza archivos temporales y ofrece detección de hablantes. **(En desarrollo)**


## Características 

- Captura de streams de YouTube en vivo
- Transcripción automática de audio a texto
- Procesamiento en tiempo real con arquitectura multihilo
- Guardado de transcripciones para consulta posterior
- Soporte para modelos Whisper y WhisperX
- Posibilidad de diarización de hablantes (WhisperX)
- **Sistema de corrección de errores en la transcripción**:
  - Corrección fonética con algoritmo Metaphone
  - Corrección tipográfica con algoritmos de similitud de cadenas
  - Sistema de caché inteligente para optimización
  - Soporte para diccionarios personalizados de palabras correctas
- **Sistema de logging integrado** para debugging y monitoreo
- **Manejo robusto de errores** y terminación controlada

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
jellyfish
unidecode
```

## Instalación

1. Clona este repositorio
   ```bash
   git clone https://github.com/Digio-Campus/Youtube-transcriber.git
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

4. En caso de utilizar WhisperX (No recomendado por el momento):


 La instalación suele dar problemas, la propia pagina de [WhisperX](https://github.com/m-bain/whisperX?tab=readme-ov-file#common-issues--troubleshooting-) tiene un apartado de solucion de problemas que puedes consultar. 


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

## Uso Whisper

### Uso básico
Para ejecutar el transcriptor de whisper con los valores predeterminados solo es necesario la url del stream:

```bash
python transcriptor-whisper.py --url "https://www.youtube.com/watch?v=STREAM_ID"
```

### Uso con logging para debugging
El sistema incluye logging automático que guarda información en `transcriptor.log`:

```bash
# Logging normal (solo errores importantes)
python transcriptor-whisper.py --url "URL_DEL_STREAM" --debug

# Ver logs en tiempo real
tail -f transcriptor.log
```

### Argumentos disponibles
Los argumentos disponibles son:
- `--url`: URL del stream de YouTube a transcribir **(requerido)**
- `--model`: Tamaño del modelo Whisper a utilizar (tiny, base, small, medium, large), predeterminado es `small`
- `--language`: Código de idioma para la transcripción (ej: es, en, fr), predeterminado se detecta automáticamente  
- `--output`: Archivo de salida para guardar la transcripción, predeterminado es `transcripcion.txt`
- `--chunk-size`: Tamaño del fragmento de audio en segundos, predeterminado es `10`
- `--correct-words`: Archivo JSON con palabras correctas para corrección de transcripciones, predeterminado no se realiza corrección
- `--debug`: Activar modo debug con logging detallado

### Ejemplos de uso:

```bash
# Transcripción básica
python transcriptor-whisper.py --url "https://www.youtube.com/watch?v=STREAM_ID"

# Con modelo más preciso y corrección de errores
python transcriptor-whisper.py --url "URL" --model medium --correct-words "palabras_correctas.json"

# Con debugging activado para diagnóstico
python transcriptor-whisper.py --url "URL" --debug

# Configuración personalizada completa
python transcriptor-whisper.py \
  --url "URL_DEL_STREAM" \
  --model large \
  --language es \
  --chunk-size 5 \
  --output mi_transcripcion.txt \
  --correct-words palabras_correctas.json \
  --debug
```

### Ejemplo de ficheros de corrección de errores:
Puedes crear un fichero de palabras correctas, por ejemplo `palabras_correctas.json`, con uno de los siguientes formatos:

- O bien una lista de palabras:

   ```json
   [
      "Ábalos",
      "Koldo",
      "UCO", 
      "malversación"
   ]
   ```

- O bien, para una mayor legibilidad, un diccionario:

   ```json
   {
      "nombres": [
      "Ábalos",
      "Koldo"
      ],
      "palabras_tecnicas": [
      "foral",
      "amaños",
      "UCO",
      "malversación"
      ],
      "partidos_politicos": [
      "Vox"
      ]
   }
   ```

### Terminación del programa

Para detener la transcripción en cualquier momento, simplemente presiona **Ctrl+C**. El programa finalizará de manera controlada, asegurándose de que todos los procesos terminen correctamente y que las transcripciones se guarden.

### Sistema de Logging

El transcriptor incluye un **sistema de logging robusto** que facilita el debugging y monitoreo:

#### Archivos generados:
- `transcripcion.txt`: Transcripción del audio (salida principal)
- `transcriptor.log`: Logs detallados del sistema (debugging)

#### Tipos de logs:
- **INFO**: Eventos importantes del sistema (inicio, fin, configuración aplicada)
- **DEBUG**: Información detallada para desarrollo (URLs obtenidas, chunks procesados)
- **ERROR**: Errores y excepciones con detalles para diagnóstico
- **WARNING**: Situaciones que requieren atención pero no detienen el proceso

## Uso WhisperX
Para ejecutar el transcriptor de whisperX, que implementa diarización, con los valores predeterminados son necesarios tanto la url del stream, como un token de Hugging Face:

```bash
python transcriptor-whisperX.py --url "https://www.youtube.com/watch?v=STREAM_ID" --token "YOUR_HG_KEY"
```

Los argumentos disponibles son, casi idénticos a los de Whisper, pero no implementa la corrección de errores y necesita un token de Hugging Face:
- `--url`: URL del stream de YouTube a transcribir
- `--token`: token de Hugging Face para descargar el modelo necesario para la diarización. Visitar la pagina de [WhisperX](https://github.com/m-bain/whisperX?tab=readme-ov-file#speaker-diarization)
- `--model`: Tamaño del modelo Whisper a utilizar (tiny, base, small, medium, large), predeterminado es `small`
- `--language`: Código de idioma para la transcripción (ej: es, en, fr), predeterminado se detecta automáticamente  
- `--output`: Archivo de salida para guardar la transcripción, predeterminado es `transcripcion.txt`
- `--chunk-size`: Tamaño del fragmento de audio en segundos, predeterminado es `10`

### Características especiales de WhisperX:


- Implementa **diarización de hablantes**: Identifica y separa las voces de diferentes hablantes en el audio.
- Utiliza **archivos temporales** para manejar la transcripción y diarización, lo que puede aumentar el uso de disco y memoria.
- No admite corrección de errores como Whisper, por lo que no se puede utilizar el argumento `--correct-words`.
- No tiene implementado un mecanismo de parada, por lo que puede dar error si se intenta detener el programa con Ctrl+C. Para finalizar la transcripción, es necesario cerrar la terminal o finalizar el proceso manualmente.


## Arquitectura del sistema

### Transcriptor Whisper (Recomendado)
El sistema utiliza una **arquitectura multihilo optimizada** con cuatro hilos independientes:

1. **Hilo de captura de audio**: Extrae audio de YouTube usando FFmpeg y yt-dlp
2. **Hilo de transcripción**: Procesa chunks de audio con el modelo Whisper
3. **Hilo de corrección**: Aplica corrección de errores usando algoritmos fonéticos y de similitud
4. **Hilo de salida**: Gestiona la escritura de resultados en archivo y consola

### Sistema de corrección de errores
El sistema utiliza un **enfoque híbrido de dos niveles**:

1. **Nivel fonético**: Utiliza el algoritmo Metaphone (implementado en `jellyfish`) para encontrar palabras que suenen similar
2. **Nivel tipográfico**: Utiliza algoritmos de similitud de cadenas (implementado en `difflib`) para corregir errores de escritura

**Optimizaciones implementadas**:
- Caché inteligente para evitar recálculos
- Pre-cálculo de índices fonéticos y listas normalizadas
- Búsquedas O(1) en conjuntos para palabras correctas
- Algoritmos optimizados para el idioma español

## Comentarios sobre los modelos de transcripción
La implementación del modelo de Whisper es bastante sencilla, ya que se basa en la librería `openai-whisper` y no requiere de una configuración compleja. Además, el procesamiento se realiza en memoria RAM, lo que permite una transcripción rápida y eficiente. Se recomienda utilizar este script.

La implementación de WhisperX es más complicada debido a la necesidad de manejar archivos temporales y la detección de hablantes, lo que añade un nivel adicional de complejidad al proyecto. El rendimiento del modelo, o al menos de esta implementación, no es tan bueno como el de Whisper,dejando incluso bloques de audio sin procesar, por lo que se recomienda utilizarlo solo si se desea usar la diarización.

## Comentarios sobre la corrección de errores

El sistema de corrección implementa una **arquitectura híbrida de dos niveles** altamente optimizada:

### Algoritmos utilizados:

1. **Corrección fonética** (Primera línea de defensa):
   - Utiliza el algoritmo **Metaphone** de la biblioteca `jellyfish` (implementado en C para máximo rendimiento)
   - Crea un índice fonético pre-calculado para búsquedas O(1)
   - Especialmente efectivo para nombres propios y palabras técnicas

2. **Corrección tipográfica** (Segunda línea de defensa):
   - Utiliza `difflib.get_close_matches()` (biblioteca estándar de Python)
   - Algoritmos de similitud de cadenas más sofisticados que la distancia de Levenshtein simple
   - Maneja mejor las variaciones acentuadas y cambios de orden de letras

### Optimizaciones implementadas:

- **Pre-cálculo de datos**: Índices fonéticos y listas normalizadas se calculan una sola vez al inicio
- **Sistema de caché inteligente**: Evita recálculos usando palabras normalizadas como clave
- **Búsquedas O(1)**: Utiliza conjuntos (sets) para verificación de palabras correctas
- **Minimización de recálculos**: Las normalizaciones se reutilizan eficientemente

### Comparación con otras bibliotecas evaluadas:

- **jellyfish**: ✅ Elegida por velocidad (C), incluye Metaphone y Levenshtein
- **pyphonetics**: ❌ Python puro, más lento, sin ventajas significativas
- **abydos**: ❌ Más complejo, sin beneficios claros sobre jellyfish
- **PyFonetika**: ❌ Optimizada para español pero menos eficiente a nivel de código 

## Estado del proyecto

✅ **Whisper funcional y optimizado** - El transcriptor Whisper está completamente operativo con sistema de corrección avanzado

🚧 **WhisperX en desarrollo** - Funcional pero con limitaciones de rendimiento

### Rendimiento y características:

- **Transcriptor Whisper**: Recomendado para uso general, alta eficiencia y corrección de errores integrada
- **WhisperX**: Útil solo si necesitas diarización de hablantes, rendimiento inferior al Whisper básico
