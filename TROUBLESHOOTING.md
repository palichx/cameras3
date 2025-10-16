# Решение проблемы "yarn.lock not found"

## Проблема

При сборке Docker возникает ошибка:
```
COPY package.json yarn.lock ./
"/yarn.lock": not found
```

## Причина

Docker не может найти yarn.lock в контексте сборки `./frontend`

## Решения

### Решение 1: Проверка файлов (СНАЧАЛА)

```bash
# Перейти в директорию frontend
cd /app/frontend

# Проверить наличие файлов
ls -la | grep -E "(package.json|yarn.lock)"

# Должно показать:
# -rw-r--r-- 1 root root   2842 package.json
# -rw-r--r-- 1 root root 584922 yarn.lock

# Проверить .dockerignore
cat .dockerignore | grep -E "(package|yarn)"

# НЕ должно показывать package.json или yarn.lock
```

### Решение 2: Обновленный .dockerignore

Файл `/app/frontend/.dockerignore` теперь содержит:

```dockerignore
# Include package files (important!)
!package.json
!yarn.lock

# Ignore everything else
node_modules
build
npm-debug.log
yarn-error.log
.DS_Store
.git
.gitignore
README.md
.env.local
.env.development.local
.env.test.local
.env.production.local
```

Знак `!` означает ИСКЛЮЧЕНИЕ - эти файлы НЕ будут игнорироваться.

### Решение 3: Раздельное копирование в Dockerfile

Файл `/app/frontend/Dockerfile` обновлен:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files separately
COPY package.json ./
COPY yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy application code
COPY . .

# Build and serve...
```

### Решение 4: Использовать debug Dockerfile

Для отладки создан `/app/frontend/Dockerfile.debug` с подробными логами.

Сборка с debug:
```bash
cd /app
docker-compose -f docker-compose.yml build --no-cache frontend
```

### Решение 5: Очистка Docker кеша

Если проблема сохраняется:

```bash
# Остановить все контейнеры
docker-compose down

# Удалить все образы проекта
docker images | grep secureview | awk '{print $3}' | xargs docker rmi -f

# Очистить весь кеш Docker
docker builder prune -a -f

# Пересобрать с нуля
docker-compose build --no-cache
```

### Решение 6: Альтернативный docker-compose.yml

Если ничего не помогает, измените `docker-compose.yml`:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    args:
      - BUILDKIT_INLINE_CACHE=1
  # ... rest of config
```

## Проверка после сборки

```bash
# Проверить, что образ собрался
docker images | grep secureview-frontend

# Запустить контейнер
docker-compose up frontend

# Проверить логи
docker-compose logs frontend

# Если успешно - увидите:
# "INFO:  Accepting connections"
```

## Тестовая сборка (без docker-compose)

```bash
cd /app/frontend

# Убедитесь, что файлы есть
ls -la package.json yarn.lock

# Прямая сборка Docker
docker build -t test-frontend .

# Если ошибка - используйте debug версию
docker build -f Dockerfile.debug -t test-frontend .
```

## Если все еще не работает

### Вариант A: Создать yarn.lock заново

```bash
cd /app/frontend

# Удалить node_modules и lock файлы
rm -rf node_modules yarn.lock

# Пересоздать yarn.lock
yarn install

# Проверить размер
ls -lh yarn.lock
# Должно быть ~500KB+

# Теперь собирать Docker
```

### Вариант B: Использовать package-lock.json вместо yarn.lock

Измените Dockerfile:

```dockerfile
# Вместо yarn использовать npm
COPY package.json package-lock.json ./
RUN npm ci

# Вместо yarn build
RUN npm run build

# Вместо yarn global add serve
RUN npm install -g serve
```

## Финальная проверка

```bash
# Все в одной команде
cd /app/frontend && \
echo "=== Files in frontend ===" && \
ls -la | grep -E "(package|yarn)" && \
echo "=== .dockerignore content ===" && \
cat .dockerignore && \
echo "=== Testing COPY command ===" && \
test -f package.json && echo "✓ package.json exists" || echo "✗ package.json missing" && \
test -f yarn.lock && echo "✓ yarn.lock exists" || echo "✗ yarn.lock missing"
```

Если все тесты показывают ✓ - файлы на месте и Docker сборка должна работать.

## Контакты для поддержки

Если проблема сохраняется, предоставьте:
1. Вывод `ls -la /app/frontend/`
2. Вывод `cat /app/frontend/.dockerignore`
3. Вывод `docker-compose build frontend 2>&1 | tail -50`
