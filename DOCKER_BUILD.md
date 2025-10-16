# Инструкция по сборке Docker образов

## Предварительные требования

- Docker версии 20.10 или выше
- Docker Compose версии 2.0 или выше
- Минимум 2GB свободной оперативной памяти
- Минимум 10GB свободного места на диске

## Проверка окружения

```bash
# Проверить версию Docker
docker --version

# Проверить версию Docker Compose
docker-compose --version

# Проверить доступность Docker
docker ps
```

## Сборка образов

### Вариант 1: Полная сборка (рекомендуется)

```bash
# Из корневой директории проекта
cd /app

# Сборка всех сервисов
docker-compose build

# Запуск
docker-compose up -d

# Проверка логов
docker-compose logs -f
```

### Вариант 2: Сборка с очисткой кеша

Если возникают проблемы со сборкой:

```bash
# Остановить все контейнеры
docker-compose down

# Удалить старые образы
docker-compose rm -f

# Очистить Docker кеш
docker system prune -a

# Пересобрать с нуля
docker-compose build --no-cache

# Запустить
docker-compose up -d
```

### Вариант 3: Построение отдельных сервисов

```bash
# Только backend
docker-compose build backend

# Только frontend
docker-compose build frontend

# Только MongoDB (не требует сборки, использует готовый образ)
docker-compose up -d mongodb
```

## Устранение проблем

### Проблема: "yarn.lock not found"

**Причина:** Файл yarn.lock заблокирован .dockerignore или отсутствует

**Решение:**
```bash
# Проверить наличие файла
ls -la frontend/yarn.lock

# Проверить .dockerignore
cat frontend/.dockerignore

# Убедиться, что yarn.lock НЕ указан в .dockerignore
```

### Проблема: "Cannot connect to Docker daemon"

**Причина:** Docker не запущен

**Решение:**
```bash
# Linux
sudo systemctl start docker

# macOS
# Запустить Docker Desktop

# Windows
# Запустить Docker Desktop
```

### Проблема: "Port already in use"

**Причина:** Порты 3000, 8001 или 27017 уже заняты

**Решение:**
```bash
# Найти процесс, использующий порт
lsof -i :3000
lsof -i :8001
lsof -i :27017

# Остановить конфликтующий процесс или изменить порты в docker-compose.yml
```

### Проблема: FFmpeg не найден в контейнере

**Причина:** Образ собран неправильно

**Решение:**
```bash
# Пересобрать backend с очисткой кеша
docker-compose build --no-cache backend

# Проверить наличие FFmpeg в контейнере
docker-compose run backend ffmpeg -version
```

## Проверка работоспособности

После успешной сборки и запуска:

```bash
# Проверить статус всех сервисов
docker-compose ps

# Все сервисы должны иметь статус "Up"

# Проверить логи
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mongodb

# Проверить доступность API
curl http://localhost:8001/api/stats

# Проверить доступность Frontend
curl http://localhost:3000
```

## Полезные команды

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Перезапуск сервиса
docker-compose restart backend

# Вход в контейнер
docker-compose exec backend bash
docker-compose exec frontend sh

# Просмотр использования ресурсов
docker stats

# Очистка неиспользуемых ресурсов
docker system prune -a --volumes
```

## Конфигурация переменных окружения

### Backend (.env не требуется в Docker)

Все переменные настроены в docker-compose.yml:
- `MONGO_URL` - подключение к MongoDB
- `DB_NAME` - имя базы данных
- `CORS_ORIGINS` - разрешенные источники

### Frontend (.env не требуется в Docker)

Переменная настроена в docker-compose.yml:
- `REACT_APP_BACKEND_URL` - URL backend API

## Производственное развертывание

Для production рекомендуется:

1. Изменить переменные окружения:
```yaml
# docker-compose.yml
frontend:
  environment:
    - REACT_APP_BACKEND_URL=https://your-domain.com
```

2. Настроить reverse proxy (nginx):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api {
        proxy_pass http://localhost:8001;
    }
}
```

3. Использовать Docker Swarm или Kubernetes для масштабирования

## Дополнительная информация

- Frontend собирается с production оптимизацией
- Backend использует uvicorn для высокой производительности
- MongoDB использует persistent volumes для сохранения данных
- Видео файлы монтируются из `./recordings` для доступа с хоста
