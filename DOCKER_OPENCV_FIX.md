# Решение проблемы "Package 'libgl1-mesa-glx' has no installation candidate"

## Причина

Пакет `libgl1-mesa-glx` был переименован в новых версиях Debian/Ubuntu.
В Python 3.11-slim (базируется на Debian Bookworm) этот пакет недоступен.

## Решение 1: Обновленный Dockerfile (РЕКОМЕНДУЕТСЯ)

Основной `/app/backend/Dockerfile` уже обновлен с правильными пакетами:

```dockerfile
# Используется libgl1 вместо libgl1-mesa-glx
libgl1
libglvnd0
libglx0
libegl1
```

**Сборка:**
```bash
cd /app
docker-compose build backend
```

## Решение 2: Минимальный Dockerfile

Если основной не работает, используйте минимальную версию:

```bash
cd /app
docker-compose build --build-arg DOCKERFILE=Dockerfile.minimal backend
```

Или измените `docker-compose.yml`:
```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.minimal  # Изменить здесь
```

## Решение 3: Ubuntu-based Dockerfile

Самый надежный вариант - использовать Ubuntu 22.04:

```bash
cd /app
docker-compose build --build-arg DOCKERFILE=Dockerfile.ubuntu backend
```

Или измените `docker-compose.yml`:
```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.ubuntu  # Изменить здесь
```

## Решение 4: Изменить docker-compose.yml

Отредактируйте `/app/docker-compose.yml`:

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.ubuntu  # Выберите: Dockerfile, Dockerfile.minimal, или Dockerfile.ubuntu
```

Затем:
```bash
docker-compose build --no-cache backend
docker-compose up -d
```

## Сравнение версий Dockerfile

| Dockerfile | Базовый образ | Размер | Совместимость | Рекомендация |
|------------|---------------|--------|---------------|--------------|
| **Dockerfile** | python:3.11-slim | ~300MB | Debian 12 | ✅ Основной |
| **Dockerfile.minimal** | python:3.11-slim | ~290MB | Debian 12 | ⚠️ Минимальный |
| **Dockerfile.ubuntu** | ubuntu:22.04 | ~400MB | Ubuntu 22.04 | ✅ Самый надежный |

## Быстрое тестирование

### Тест 1: Основной Dockerfile
```bash
cd /app/backend
docker build -t test-backend .
```

Если успех - используйте его.

### Тест 2: Минимальный
```bash
cd /app/backend
docker build -f Dockerfile.minimal -t test-backend .
```

### Тест 3: Ubuntu
```bash
cd /app/backend
docker build -f Dockerfile.ubuntu -t test-backend .
```

## Проверка после сборки

```bash
# Проверить, что OpenCV работает
docker run --rm test-backend python -c "import cv2; print(cv2.__version__)"

# Проверить FFmpeg
docker run --rm test-backend ffmpeg -version

# Запустить сервер
docker-compose up backend
```

## Полная пересборка

Если возникают проблемы с кешем:

```bash
# Очистить все
docker-compose down -v
docker system prune -a -f

# Выбрать нужный Dockerfile в docker-compose.yml
nano docker-compose.yml

# Пересобрать с нуля
docker-compose build --no-cache --pull
docker-compose up -d
```

## Рекомендуемая конфигурация

Для максимальной совместимости измените `docker-compose.yml`:

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.ubuntu  # Используем Ubuntu для надежности
    container_name: secureview-backend
    restart: unless-stopped
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=secureview_db
      - CORS_ORIGINS=*
    ports:
      - "8001:8001"
    volumes:
      - ./recordings:/app/recordings
    depends_on:
      - mongodb
    networks:
      - secureview-network
```

Затем:
```bash
docker-compose build backend
docker-compose up -d
```

## Если все еще не работает

### Вариант A: Использовать готовый образ с OpenCV

Создайте `Dockerfile.opencv`:

```dockerfile
FROM jjanzic/docker-python3-opencv:latest

WORKDIR /app

# Install additional dependencies
RUN apt-get update && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/recordings

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Вариант B: Установить только headless OpenCV

Измените `requirements.txt`:

```txt
# Вместо opencv-python используйте headless версию
opencv-python-headless==4.8.1.78
opencv-contrib-python-headless==4.8.1.78
```

Тогда не нужны GUI библиотеки вообще:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Только FFmpeg нужен
RUN apt-get update && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/recordings

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Проверка логов сборки

Если сборка падает, смотрите логи:

```bash
docker-compose build backend 2>&1 | tee build.log
cat build.log | grep -i error
```

Предоставьте эти логи для дальнейшей диагностики.
