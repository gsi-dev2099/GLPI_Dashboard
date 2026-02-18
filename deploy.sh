#!/bin/bash

echo "🚀 Iniciando despliegue de GLPI Dashboard..."

# 1. Detener versiones previas (si existen)
echo "🛑 Deteniendo contenedores anteriores..."
docker-compose down

# 2. Construir la imagen y levantar el servicio en segundo plano
echo "🔨 Construyendo y levantando servicios..."
docker-compose up -d --build

# 3. Mostrar estado
if [ $? -eq 0 ]; then
    echo "✅ Despliegue exitoso!"
    echo "🌍 Accede a: http://TU_IP:8846"
    echo "📜 Mostrando logs (Ctrl+C para salir)..."
    echo "-----------------------------------------"
    docker-compose logs -f
else
    echo "❌ Error en el despliegue."
fi
