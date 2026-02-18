# Base Image: Python 3.10 Slim (Ligerísimo)
FROM python:3.10-slim

# Directorio de trabajo
WORKDIR /app

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema (si scikit-learn o mysql necesitan compiladores)
# Para asyncmy/mariadb a veces se requiere gcc. Lo instalamos por si acaso y limpiamos.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto solicitado
EXPOSE 8846

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8846"]
