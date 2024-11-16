**Documentación del Proyecto del Chatbot para Desarrolladores Backend**

### Descripción del Proyecto
Este proyecto es un chatbot diseñado para interactuar con usuarios, almacenando información en una base de datos y utilizando una arquitectura modular que facilita su mantenimiento y expansión. El sistema combina un frontend sencillo con un backend robusto, proporcionando una experiencia de usuario fluida e intuitiva. La modularidad del proyecto permite a los desarrolladores agregar nuevas características y adaptarse rápidamente a los cambios en los requerimientos del negocio.

### Estructura del Proyecto
1. **Raíz del Proyecto**
   - **.gitignore**: Define qué archivos deben ser ignorados por Git, asegurando que los archivos sensibles o innecesarios no se suban al repositorio.
   - **README.md**: Documentación esencial para ayudar a los nuevos desarrolladores a comprender cómo desplegar y trabajar con el proyecto. Contiene instrucciones para la configuración y el uso del chatbot.
   - **api_keys.json**: Archivo para almacenar las claves API necesarias para integrar servicios externos, como OpenAI. Estas claves se utilizan para la generación de respuestas y otras funciones que requieren servicios externos.
   - **chatbot.db**: Base de datos SQLite que almacena información relevante, como datos de usuarios, preguntas frecuentes, productos y pedidos.
   - **main.py**: Punto de entrada principal del servidor. Inicia la aplicación y conecta todos los componentes necesarios para el funcionamiento del chatbot.
   - **requirements.txt**: Lista de dependencias del proyecto. Utilizando este archivo, los desarrolladores pueden instalar todas las bibliotecas requeridas de manera rápida y eficiente.
   - **frontend**: Carpeta que contiene la interfaz de usuario, proporcionando una manera visual y amigable para que los usuarios interactúen con el chatbot.

2. **Carpeta `app` (Backend Principal)**
   - **config.py**: Contiene configuraciones generales del proyecto, tales como parámetros del servidor y configuraciones globales utilizadas en diferentes partes de la aplicación.
   - **crud.py**: Incluye las funciones CRUD (Crear, Leer, Actualizar, Eliminar) para manipular la información almacenada en la base de datos. Estas funciones centralizan las operaciones de la base de datos, facilitando el mantenimiento del código.
   - **database.py**: Maneja la configuración de la conexión con la base de datos. Utiliza SQLAlchemy para facilitar la gestión de transacciones y la conexión a SQLite.
   - **models.py**: Define los modelos de datos utilizando SQLAlchemy. Estos modelos representan las tablas de la base de datos y las relaciones entre ellas, simplificando el manejo de datos complejos.
   - **schemas.py**: Define los esquemas de datos que se usan para validar la entrada y la salida en los endpoints de la API, asegurando que los datos procesados sean consistentes y seguros.
   - **routes**: Carpeta que contiene las rutas o endpoints del servidor. Cada archivo dentro de `routes` gestiona funcionalidades específicas, organizando las solicitudes en áreas como gestión de usuarios, pedidos, productos, etc. Esto hace que la aplicación sea más modular y facilita el desarrollo y mantenimiento.

3. **Carpeta `frontend` (Interfaz de Usuario)**
   - **index.html**: Archivo principal que define la estructura visual de la interfaz de usuario.
   - **script.js**: Contiene la lógica del frontend, permitiendo que el usuario interactúe con el backend mediante solicitudes HTTP y maneje las respuestas del chatbot.
   - **styles.css**: Define la apariencia visual del frontend, asegurando una experiencia de usuario coherente y atractiva.

### Flujo de la Aplicación
1. **Inicio del Servidor**
   - El archivo `main.py` es el punto de inicio del servidor, utilizando **FastAPI** o **Flask** para manejar las peticiones HTTP. Esto permite a los usuarios interactuar con el chatbot a través de la web.

2. **Conexión a la Base de Datos**
   - La base de datos utilizada es **SQLite**, y la configuración de la conexión se encuentra en `database.py`. Se utiliza **SQLAlchemy** como ORM para manejar las transacciones y la persistencia de datos de manera eficiente y segura.

3. **Operaciones CRUD**
   - Las funciones CRUD están definidas en `crud.py`. Estas funciones se utilizan para gestionar los datos del proyecto, permitiendo agregar, leer, actualizar y eliminar registros en la base de datos.

4. **Validación de Datos**
   - `schemas.py` define las estructuras de datos necesarias para validar las entradas y salidas en los endpoints. Esto garantiza que el sistema siempre reciba y devuelva datos en un formato correcto.

5. **Rutas de la API**
   - Las rutas de la API están organizadas en la carpeta `routes`. Cada ruta se asocia con un conjunto específico de funcionalidades, como la gestión de usuarios o la creación de pedidos, lo cual hace que el código sea más modular y comprensible.

### Flujo de Mensajes del Chatbot
El archivo `chatbot.py` es el componente central del flujo de mensajes. Aquí se explica cómo funciona el flujo completo de mensajes dentro del sistema:

1. **Recepción del Mensaje**
   - Los mensajes de los usuarios se reciben a través de un endpoint específico definido en `routes`. Los usuarios interactúan con el chatbot mediante solicitudes HTTP POST, las cuales se procesan en el backend.

2. **Procesamiento del Mensaje**
   - Una vez recibido, el mensaje se envía a `ChatbotService.ask_question()`, donde se realiza la validación inicial. Durante este proceso, se identifica el contexto del usuario y la intención del mensaje para asegurar una respuesta adecuada.

3. **Flujo de Funciones Dependiendo de la Intención**
   - El mensaje se procesa según la intención identificada:
     - **FAQ (Preguntas Frecuentes)**: Si el mensaje coincide con una pregunta frecuente, se llama a `ChatbotService.search_faq_in_db()`. Esta función utiliza el modelo de embeddings `SentenceTransformer` para identificar la respuesta más adecuada en la base de datos de FAQ.
     - **Consultar Productos por Ciudad**: Si la intención es obtener información sobre la disponibilidad de productos en una ciudad específica, se utiliza `client.chat.completions.create()` para generar una respuesta que indique los productos disponibles en esa ciudad.
     - **Creación de una Orden**: Si el mensaje tiene la intención de realizar un pedido, y se cuenta con toda la información necesaria (nombre, dirección, producto, etc.), se llama a `ChatbotService.create_order_from_context()` para registrar el pedido.
     - **Consulta General de Productos**: Para solicitudes generales sobre productos, `crud_producto.get_productos_by_cuenta()` se utiliza para obtener los productos disponibles para una cuenta específica.
     - **Intención Desconocida**: Si no se puede identificar claramente la intención, se utiliza `ChatbotService.search_faq_in_db()` para buscar una respuesta adecuada en la base de datos de FAQ. Si no se encuentra una respuesta relevante, se envía un mensaje solicitando más detalles al usuario.

4. **Consulta a la Base de Datos**
   - Dependiendo de la intención del usuario, el chatbot puede necesitar consultar la base de datos. Por ejemplo, si el usuario pregunta por el estado de un pedido o información sobre productos, se utilizan funciones CRUD para obtener la información necesaria.

5. **Generación de la Respuesta**
   - Con los datos recopilados, se llama a `ChatbotService.generate_humanlike_response()`. Esta función construye un prompt para `OpenAI GPT-4`, asegurando que las respuestas sean precisas y basadas únicamente en la información disponible en la base de datos.

6. **Envío de la Respuesta al Usuario**
   - La respuesta se envía al frontend en formato JSON. El archivo `script.js` del frontend se encarga de mostrar esta respuesta al usuario de manera amigable, asegurando una experiencia de comunicación fluida.

### Tecnologías Utilizadas
- **Backend**: Python, FastAPI o Flask, SQLAlchemy, SQLite.
- **Frontend**: HTML, CSS, JavaScript.

### Despliegue del Proyecto
Para desplegar el proyecto localmente, siga estos pasos:

1. **Clonar el Repositorio**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd chatbot_project-main
   ```

2. **Instalar Dependencias**
   Asegúrese de tener **Python 3.8+** instalado y ejecute:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar el Entorno**
   Cree un archivo `.env` en la raíz del proyecto con las siguientes configuraciones:
   ```
   DATABASE_URL=sqlite:///chatbot.db
   API_KEY=<tu_clave_api>
   SECRET_KEY=<tu_secret_key>
   DEBUG=True
   PORT=8000
   ```

4. **Inicializar la Base de Datos**
   Verifique que el archivo de la base de datos esté disponible o inicialice una nueva base de datos ejecutando el script de `database.py`.

5. **Ejecutar el Servidor**
   Ejecute el archivo principal para iniciar la aplicación:
   ```bash
   python main.py
   ```
   El servidor estará disponible en `http://127.0.0.1:8000`.

### Despliegue en Producción en Railway
Para desplegar este proyecto en **Railway**, siga los siguientes pasos:

1. **Crear un Proyecto en Railway**
   - Ingrese a [Railway](https://railway.app) y cree un nuevo proyecto.

2. **Subir el Código**
   - Puede conectar su repositorio de GitHub directamente con Railway o subir el código manualmente.

3. **Configurar Variables de Entorno**
   - En la configuración del proyecto en Railway, agregue las variables de entorno especificadas en el archivo `.env`:
     - `DATABASE_URL`
     - `API_KEY`
     - `SECRET_KEY`
     - `PORT`

4. **Desplegar la Aplicación**
   - Railway detectará automáticamente el archivo `main.py` y comenzará a desplegar la aplicación.
   - Una vez completado el despliegue, Railway proporcionará una URL pública para acceder al chatbot.

### Datos del `.env` Faltantes
- **DATABASE_URL**: URL de la base de datos, como `sqlite:///chatbot.db`.
- **API_KEY**: Clave utilizada para integraciones externas. Debe mantenerse segura.
- **SECRET_KEY**: Clave utilizada para la autenticación de tokens, asegurando la integridad de la aplicación.
- **PORT**: Puerto en el que se ejecutará la aplicación (por ejemplo, `8000`).

### Buenas Prácticas
1. **Seguridad**: Mantenga seguro el archivo `.env` y evite que se suba al repositorio.
2. **Modularidad**: Siga un esquema modular al agregar nuevas funcionalidades. Mantenga las rutas, los modelos y los esquemas organizados para facilitar futuras expansiones.
3. **Manejo de Errores**: Implemente un manejo adecuado de errores para brindar una buena experiencia de usuario, evitando respuestas incompletas o comportamientos inesperados.
