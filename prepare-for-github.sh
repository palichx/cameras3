#!/bin/bash

echo "========================================"
echo "Подготовка файлов для GitHub"
echo "========================================"
echo ""

cd /app

# Проверка 1: Git инициализирован?
if [ ! -d ".git" ]; then
    echo "Git не инициализирован. Инициализирую..."
    git init
    git branch -M main
fi

echo "1. Проверка статуса yarn.lock..."
if git ls-files --error-unmatch frontend/yarn.lock 2>/dev/null; then
    echo "   ✓ frontend/yarn.lock уже в git"
else
    echo "   ⚠ frontend/yarn.lock не в git, добавляю..."
    git add frontend/yarn.lock
fi

echo ""
echo "2. Проверка других важных файлов..."

# Список критичных файлов
critical_files=(
    "frontend/package.json"
    "frontend/yarn.lock"
    "frontend/Dockerfile"
    "backend/requirements.txt"
    "backend/Dockerfile"
    "docker-compose.yml"
    ".gitignore"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        if git ls-files --error-unmatch "$file" 2>/dev/null; then
            echo "   ✓ $file в git"
        else
            echo "   + Добавляю $file"
            git add "$file"
        fi
    else
        echo "   ✗ $file не найден!"
    fi
done

echo ""
echo "3. Проверка .gitignore..."
if grep -q "^yarn\.lock$" .gitignore; then
    echo "   ✗ ОШИБКА: yarn.lock полностью игнорируется в .gitignore!"
    echo "   Исправляю..."
    sed -i '/^yarn\.lock$/d' .gitignore
fi

if grep -q "^\*\.lock$" .gitignore; then
    echo "   ✗ ОШИБКА: *.lock игнорируется в .gitignore!"
    echo "   Исправляю..."
    sed -i '/^\*\.lock$/d' .gitignore
fi

echo "   ✓ .gitignore корректен"

echo ""
echo "4. Текущий статус git..."
git status --short | head -20

echo ""
echo "========================================"
echo "Готово к commit и push"
echo "========================================"
echo ""
echo "Выполните следующие команды:"
echo ""
echo "  # Добавить все файлы"
echo "  git add ."
echo ""
echo "  # Создать commit"
echo "  git commit -m 'Add SecureView video surveillance system'"
echo ""
echo "  # Добавить remote (если еще не добавлен)"
echo "  git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo ""
echo "  # Push на GitHub"
echo "  git push -u origin main"
echo ""
echo "Или выполните всё сразу:"
echo ""
echo "  git add . && git commit -m 'Add SecureView system' && git push -u origin main"
echo ""
