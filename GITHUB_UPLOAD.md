# Руководство по загрузке на GitHub

## ✅ Статус: Все файлы готовы к push

### Проверено и добавлено в git:

- ✅ frontend/yarn.lock (572KB)
- ✅ frontend/package.json
- ✅ frontend/Dockerfile
- ✅ backend/requirements.txt
- ✅ backend/Dockerfile
- ✅ docker-compose.yml
- ✅ .gitignore (очищен и корректен)
- ✅ .gitattributes (создан)

### Быстрый старт

```bash
cd /app

# 1. Добавить все файлы
git add .

# 2. Создать commit
git commit -m "Initial commit: SecureView video surveillance system

Features:
- 20 camera support with RTSP/RTP/HTTP
- Motion detection using MOG2 algorithm
- Pre/post recording (0-30s / 0-60s)
- Live view via WebSocket
- Video recording with auto-conversion
- Telegram integration
- Performance profiles (low/medium/high)
- Docker deployment ready"

# 3. Добавить remote (замените на ваш репозиторий)
git remote add origin https://github.com/YOUR_USERNAME/secureview.git

# 4. Push на GitHub
git push -u origin main
```

## Пошаговая инструкция

### Шаг 1: Проверка файлов

```bash
# Запустить автоматическую проверку
cd /app
./prepare-for-github.sh
```

Все критичные файлы должны быть помечены ✓

### Шаг 2: Убедиться, что yarn.lock в staging

```bash
git status | grep yarn.lock
```

Должно показать:
```
	new file:   frontend/yarn.lock
```

Если показывает как игнорируемый:
```bash
# Принудительно добавить
git add -f frontend/yarn.lock

# Проверить снова
git status frontend/yarn.lock
```

### Шаг 3: Проверить .gitignore

```bash
# Убедиться, что yarn.lock НЕ игнорируется глобально
grep -E "^yarn\.lock$|^\*\.lock$" .gitignore

# Если найдено - удалить эти строки
```

Правильный .gitignore должен содержать:
```gitignore
# Ignore ONLY root yarn.lock
/yarn.lock

# NOT this (WRONG!):
# yarn.lock
# *.lock
```

### Шаг 4: Создать хороший commit message

```bash
git add .

git commit -m "feat: Add SecureView video surveillance system

Complete video surveillance system with:
- Multi-camera support (up to 20 cameras)
- Advanced motion detection (MOG2)
- Intelligent recording (pre/post motion capture)
- Real-time streaming
- Telegram notifications
- Docker deployment

Technical stack:
- Backend: FastAPI + OpenCV + MongoDB
- Frontend: React + Tailwind CSS + Shadcn UI
- Deployment: Docker Compose"
```

### Шаг 5: Настроить remote

Если репозиторий уже существует на GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/secureview.git
```

Или если клонировали, remote уже настроен:
```bash
git remote -v
# Должно показать origin
```

### Шаг 6: Push на GitHub

```bash
# Первый push
git push -u origin main

# Или если ветка называется master
git push -u origin master

# Если требуется форс push (осторожно!)
git push -u origin main --force
```

## Проверка на GitHub

После push перейдите на GitHub и проверьте:

### 1. Файл yarn.lock присутствует

```
https://github.com/YOUR_USERNAME/secureview/blob/main/frontend/yarn.lock
```

Файл должен:
- Существовать
- Иметь размер ~572KB
- Содержать зависимости (не быть пустым)

### 2. Структура проекта правильная

```
secureview/
├── frontend/
│   ├── yarn.lock          ← ДОЛЖЕН БЫТЬ
│   ├── package.json       ← ДОЛЖЕН БЫТЬ
│   └── Dockerfile
├── backend/
│   ├── requirements.txt   ← ДОЛЖЕН БЫТЬ
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

### 3. .gitignore корректен

Откройте на GitHub:
```
https://github.com/YOUR_USERNAME/secureview/blob/main/.gitignore
```

Проверьте, что там НЕТ:
- ❌ `yarn.lock` (без слеша)
- ❌ `*.lock`
- ❌ `package-lock.json` (без слеша)

Должно быть только:
- ✅ `/yarn.lock` (с слешем - только корневой)
- ✅ `yarn-error.log*`
- ✅ `yarn-debug.log*`

## Решение проблем

### Проблема: yarn.lock не появляется на GitHub

**Причина 1:** Файл не был добавлен в commit

**Решение:**
```bash
git add frontend/yarn.lock
git commit --amend --no-edit
git push --force
```

**Причина 2:** Файл игнорируется .gitignore

**Решение:**
```bash
# Проверить
git check-ignore -v frontend/yarn.lock

# Если игнорируется - исправить .gitignore
# Удалить строки: yarn.lock или *.lock

# Добавить принудительно
git add -f frontend/yarn.lock
git commit -m "Add yarn.lock"
git push
```

**Причина 3:** Файл пустой или поврежден

**Решение:**
```bash
cd /app/frontend

# Проверить размер
ls -lh yarn.lock
# Должно быть 500KB+, не 86 bytes!

# Если пустой - пересоздать
rm yarn.lock
yarn install
git add yarn.lock
git commit -m "Regenerate yarn.lock"
git push
```

### Проблема: GitHub показывает "This file is empty"

Это значит файл был добавлен пустым.

**Решение:**
```bash
cd /app/frontend

# Пересоздать lock файл
rm yarn.lock
yarn install

# Проверить содержимое
head -20 yarn.lock
# Должны быть реальные зависимости

# Добавить в git
git add yarn.lock
git commit -m "Fix: Add proper yarn.lock with dependencies"
git push
```

## Быстрая проверка перед push

Одна команда для полной проверки:

```bash
cd /app && \
echo "=== Git Status ===" && \
git status --short | grep -E "(yarn|package)" && \
echo "=== File Sizes ===" && \
ls -lh frontend/yarn.lock frontend/package.json && \
echo "=== Staged Files ===" && \
git diff --cached --name-only | grep -E "(yarn|package)" && \
echo "=== Check Ignore ===" && \
git check-ignore -v frontend/yarn.lock 2>&1 || echo "✓ NOT ignored" && \
echo "=== Ready to push! ==="
```

Если все OK - можно делать push!

## После успешного push

Проверьте сборку на другой машине:

```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/secureview.git
cd secureview

# Проверить yarn.lock
ls -lh frontend/yarn.lock
# Должно быть 500KB+

# Собрать Docker
docker-compose build
docker-compose up -d

# Проверить
docker-compose ps
```

Если всё работает - успех! 🎉
