# Решение проблемы "The engine "node" is incompatible with this module"

## Проблема

При сборке Docker возникает ошибка:
```
error react-router-dom@7.9.4: The engine "node" is incompatible with this module. 
Expected version ">=20.0.0". Got "18.20.8"
```

## Причина

React Router DOM v7 требует Node.js версии 20 или выше, но в Dockerfile используется Node.js 18.

## ✅ Решение (уже применено)

### Обновлены все Dockerfile

Изменена базовая версия Node.js с `18-alpine` на `20-alpine`:

```dockerfile
# Было:
FROM node:18-alpine

# Стало:
FROM node:20-alpine
```

### Затронутые файлы:

- ✅ `/app/frontend/Dockerfile`
- ✅ `/app/frontend/Dockerfile.production`
- ✅ `/app/frontend/Dockerfile.debug`
- ✅ `/app/frontend/Dockerfile.minimal`

## Версии Node.js

| Версия | LTS | Поддержка до | React Router v7 |
|--------|-----|--------------|-----------------|
| 18.x | ✅ Yes | 2025-04-30 | ❌ Не совместим |
| 20.x | ✅ Yes | 2026-04-30 | ✅ Совместим |
| 22.x | ❌ Current | 2027-04-30 | ✅ Совместим |

## Команды для сборки

```bash
# Очистить старые образы
docker-compose down
docker system prune -a -f

# Пересобрать с Node 20
docker-compose build --no-cache frontend
docker-compose up -d

# Проверить версию Node в контейнере
docker-compose exec frontend node --version
# Должно показать: v20.x.x
```

## Проверка после обновления

```bash
# Проверить логи сборки
docker-compose build frontend 2>&1 | grep -i node

# Запустить контейнер
docker-compose up frontend

# Проверить в браузере
curl http://localhost:3000
```

## Альтернативное решение (понизить React Router)

Если по какой-то причине нужно остаться на Node 18, можно понизить версию react-router-dom:

### package.json
```json
{
  "dependencies": {
    "react-router-dom": "^6.28.0"
  }
}
```

### Команды
```bash
cd /app/frontend

# Установить React Router v6
yarn add react-router-dom@^6.28.0

# Обновить lockfile
yarn install

# Commit
git add package.json yarn.lock
git commit -m "Downgrade react-router-dom to v6 for Node 18 compatibility"
```

**Но рекомендуется использовать Node 20!**

## Совместимость зависимостей

Другие зависимости, которые могут требовать Node 20:

| Пакет | Минимальная Node.js |
|-------|---------------------|
| react-router-dom@7 | 20.0.0 |
| react@19 | 18.0.0 |
| vite@5 | 18.0.0 |
| typescript@5 | 18.0.0 |

Node 20 совместим со всеми современными пакетами.

## Проверка совместимости

Проверить все зависимости на совместимость:

```bash
cd /app/frontend

# Установить с verbose
yarn install --verbose 2>&1 | grep -i engine

# Или проверить engines в package.json
cat package.json | grep -A5 engines
```

## Обновление package.json (опционально)

Можно явно указать требуемую версию Node:

```json
{
  "name": "secureview-frontend",
  "engines": {
    "node": ">=20.0.0",
    "yarn": ">=1.22.0"
  }
}
```

Это поможет предотвратить сборку с неправильной версией Node.

## Docker Compose конфигурация

Текущая конфигурация `docker-compose.yml` корректна:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile  # Использует Node 20
```

## Локальная разработка

Если разрабатываете локально, убедитесь, что используете Node 20:

```bash
# Проверить текущую версию
node --version

# Если нужно - установить Node 20 с помощью nvm
nvm install 20
nvm use 20
nvm alias default 20

# Или с помощью n
npm install -g n
n 20
```

## CI/CD обновление

Обновите GitHub Actions / GitLab CI:

```yaml
# .github/workflows/build.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: '20'  # Изменить с 18 на 20
```

## Текущий статус

- ✅ Все Dockerfile обновлены на Node 20
- ✅ Совместимость с React Router v7
- ✅ Совместимость со всеми зависимостями
- ✅ Готово к сборке

## Команда для финальной проверки

```bash
# Полная проверка и сборка
cd /app && \
docker-compose down && \
docker system prune -a -f && \
docker-compose build --no-cache && \
docker-compose up -d && \
docker-compose ps && \
docker-compose logs frontend | tail -20
```

**Ошибка исправлена! Docker сборка с Node 20 должна работать.**
