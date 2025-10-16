# Инструкция по развертыванию через Git

## Важная информация о yarn.lock

### Структура файлов

В проекте есть два типа lock-файлов:

1. **`/app/yarn.lock`** (корневой) - ИГНОРИРУЕТСЯ в .gitignore
   - Это пустой файл, который иногда создается по ошибке
   - НЕ должен попадать в git
   - НЕ используется при сборке

2. **`/app/frontend/yarn.lock`** - ДОЛЖЕН быть в git
   - Это рабочий файл с зависимостями (572KB)
   - ОБЯЗАТЕЛЬНО должен попадать в git
   - Используется при сборке Docker

## Проверка перед коммитом

```bash
# Убедитесь, что правильный yarn.lock НЕ игнорируется
cd /app
git check-ignore -v frontend/yarn.lock
# Должно вывести: "File is NOT ignored"

# Убедитесь, что корневой yarn.lock игнорируется
git check-ignore -v yarn.lock
# Должно вывести: ".gitignore:35:/yarn.lock	yarn.lock"

# Проверьте статус
git status
# Должно показать: "Untracked files: frontend/yarn.lock"
```

## Добавление файлов в git

```bash
# Из корня проекта
cd /app

# Добавить все необходимые файлы
git add .

# Проверить, что frontend/yarn.lock включен
git status | grep yarn.lock
# Должно показать: new file:   frontend/yarn.lock

# Закоммитить
git commit -m "Initial commit: SecureView surveillance system"

# Отправить в репозиторий
git push origin main
```

## Клонирование и сборка

После клонирования репозитория:

```bash
# Клонировать
git clone <repository-url>
cd secureview

# Проверить наличие важных файлов
ls -la frontend/yarn.lock
ls -la frontend/package.json
ls -la backend/requirements.txt

# Если файлы на месте - можно собирать
docker-compose build
docker-compose up -d
```

## Проверка .gitignore

Содержимое `/app/.gitignore`:

```gitignore
# Ignore root yarn.lock (only use frontend/yarn.lock)
/yarn.lock
/package-lock.json
```

Это правило игнорирует только yarn.lock в корне, но НЕ игнорирует `frontend/yarn.lock`.

## Устранение проблем

### Проблема: "yarn.lock not found" при сборке Docker

**Причина 1:** Файл не попал в git

**Решение:**
```bash
# Проверить наличие в git
git ls-files | grep yarn.lock

# Если нет - добавить
git add frontend/yarn.lock
git commit -m "Add yarn.lock"
git push
```

**Причина 2:** Файл игнорируется .gitignore или .dockerignore

**Решение:**
```bash
# Проверить .gitignore
cat .gitignore | grep yarn

# Проверить .dockerignore
cat frontend/.dockerignore | grep yarn

# yarn.lock НЕ должен быть в этих файлах
# (только yarn-error.log и yarn-debug.log)
```

**Причина 3:** Пустой yarn.lock в корне блокирует правильный

**Решение:**
```bash
# Удалить пустой файл из корня
rm /app/yarn.lock

# Убедиться, что правильный файл существует
ls -lh frontend/yarn.lock
# Должно показать: 572K
```

## Проверка целостности после клонирования

```bash
# После git clone
cd secureview

# 1. Проверить размер yarn.lock
ls -lh frontend/yarn.lock
# Должно быть ~572KB, не 86 байт!

# 2. Проверить первые строки
head -5 frontend/yarn.lock
# Должно содержать реальные зависимости, не только комментарий

# 3. Проверить package.json
cat frontend/package.json | grep "name"
# Должно показать реальное имя проекта

# 4. Если все ОК - собирать
docker-compose build
```

## Что должно быть в репозитории

### Обязательные файлы для сборки:

```
/app/
├── docker-compose.yml
├── .gitignore (с /yarn.lock)
├── README.md
├── DOCKER_BUILD.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py
│   ├── models.py
│   ├── camera_manager.py
│   └── .dockerignore
└── frontend/
    ├── Dockerfile
    ├── package.json         ← ОБЯЗАТЕЛЕН
    ├── yarn.lock           ← ОБЯЗАТЕЛЕН (572KB!)
    ├── .dockerignore
    ├── public/
    └── src/
```

### Файлы, которые НЕ должны быть в git:

```
/yarn.lock              ← Корневой (игнорируется)
/package-lock.json      ← Корневой (игнорируется)
node_modules/           ← Везде (игнорируется)
build/                  ← Frontend build (игнорируется)
recordings/             ← Видео файлы (игнорируются)
*.env                   ← Секреты (игнорируются)
__pycache__/           ← Python cache (игнорируется)
```

## Быстрая проверка

Одна команда для проверки всего:

```bash
cd /app && \
echo "=== Checking git status ===" && \
git status | grep -E "(yarn\.lock|package\.json)" && \
echo "=== Checking file sizes ===" && \
ls -lh frontend/yarn.lock frontend/package.json && \
echo "=== Checking .gitignore ===" && \
git check-ignore -v yarn.lock && \
echo "=== Checking frontend/yarn.lock is NOT ignored ===" && \
git check-ignore -v frontend/yarn.lock || echo "✓ frontend/yarn.lock is NOT ignored"
```

Если все команды выполнились без ошибок - можно коммитить и пушить!
