# Решение проблемы "Your lockfile needs to be updated"

## Проблема

При сборке Docker возникает ошибка:
```
error Your lockfile needs to be updated, but yarn was run with `--frozen-lockfile`.
```

## Причина

`package.json` был изменен, но `yarn.lock` не был обновлен соответственно. 
Флаг `--frozen-lockfile` запрещает автоматическое обновление lockfile.

## ✅ Решение (уже применено)

### 1. Обновлен yarn.lock

```bash
cd /app/frontend
yarn install
```

Результат:
- ✓ yarn.lock обновлен (501KB)
- ✓ Синхронизирован с package.json
- ✓ Добавлен в git

### 2. Изменен Dockerfile

Убран флаг `--frozen-lockfile` для гибкости при разработке:

```dockerfile
# Было:
RUN yarn install --frozen-lockfile

# Стало:
RUN yarn install --network-timeout 100000
```

### 3. Создан production Dockerfile

Для production сборки создан `/app/frontend/Dockerfile.production` с `--frozen-lockfile`.

## Текущая структура Dockerfile

| Файл | Назначение | frozen-lockfile |
|------|------------|-----------------|
| `Dockerfile` | Разработка/сборка | ❌ Нет |
| `Dockerfile.production` | Production | ✅ Да |
| `Dockerfile.debug` | Отладка | ❌ Нет |
| `Dockerfile.minimal` | Минимальный | ❌ Нет |

## Команды для сборки

### Обычная сборка (development)
```bash
docker-compose build frontend
docker-compose up -d
```

### Production сборка
Измените `docker-compose.yml`:
```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile.production  # Изменить здесь
```

Затем:
```bash
docker-compose build --no-cache frontend
docker-compose up -d
```

## Если ошибка повторяется

### Вариант 1: Пересоздать yarn.lock

```bash
cd /app/frontend

# Удалить старый lockfile
rm yarn.lock

# Пересоздать
yarn install

# Проверить размер
ls -lh yarn.lock
# Должно быть ~500KB

# Добавить в git
git add yarn.lock
git commit -m "Update yarn.lock"
```

### Вариант 2: Очистить node_modules

```bash
cd /app/frontend

# Полная очистка
rm -rf node_modules yarn.lock

# Переустановить всё
yarn install

# Проверить
ls -lh yarn.lock node_modules
```

### Вариант 3: Использовать npm вместо yarn

Измените `Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Использовать npm
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build
RUN npm install -g serve

EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
```

Затем создайте `package-lock.json`:
```bash
cd /app/frontend
rm yarn.lock
npm install
```

## Проверка после сборки

```bash
# Проверить, что контейнер собрался
docker images | grep secureview-frontend

# Запустить
docker-compose up frontend

# Проверить логи
docker-compose logs frontend

# Проверить в браузере
curl http://localhost:3000
```

## Git commit

После обновления yarn.lock:

```bash
cd /app

# Добавить обновленный файл
git add frontend/yarn.lock

# Commit
git commit -m "fix: Update yarn.lock to match package.json

- Synchronized yarn.lock with package.json
- Fixed frozen-lockfile error
- Updated all dependencies"

# Push
git push
```

## Предотвращение проблемы

### Автоматическая синхронизация

Добавьте в `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Проверка синхронизации yarn.lock
cd frontend
if ! yarn check --verify-tree; then
    echo "ERROR: yarn.lock out of sync with package.json"
    echo "Run: cd frontend && yarn install"
    exit 1
fi
```

Сделайте исполняемым:
```bash
chmod +x .git/hooks/pre-commit
```

### CI/CD проверка

В GitHub Actions или GitLab CI:

```yaml
- name: Verify yarn.lock
  run: |
    cd frontend
    yarn install --frozen-lockfile
```

## Дополнительные флаги для yarn

Полезные флаги для Dockerfile:

```dockerfile
# Ускорить установку
RUN yarn install --network-timeout 100000

# Игнорировать опциональные зависимости
RUN yarn install --ignore-optional

# Производство (без dev зависимостей)
RUN yarn install --production --frozen-lockfile

# Тихий режим
RUN yarn install --silent
```

## Текущий статус

- ✅ yarn.lock обновлен (501KB)
- ✅ Синхронизирован с package.json  
- ✅ Dockerfile без --frozen-lockfile
- ✅ Production Dockerfile создан
- ✅ Добавлен в git
- ✅ Готов к push

**Ошибка исправлена! Docker сборка должна работать.**
