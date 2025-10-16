#!/bin/bash

echo "======================================"
echo "Проверка файлов для Docker сборки"
echo "======================================"
echo ""

# Проверка 1: Наличие файлов
echo "1. Проверка наличия файлов в /app/frontend:"
cd /app/frontend
if [ -f "package.json" ]; then
    echo "   ✓ package.json найден ($(stat -c%s package.json) bytes)"
else
    echo "   ✗ package.json НЕ НАЙДЕН!"
    exit 1
fi

if [ -f "yarn.lock" ]; then
    size=$(stat -c%s yarn.lock)
    echo "   ✓ yarn.lock найден ($size bytes)"
    if [ $size -lt 1000 ]; then
        echo "   ⚠ ВНИМАНИЕ: yarn.lock слишком мал ($size bytes)!"
    fi
else
    echo "   ✗ yarn.lock НЕ НАЙДЕН!"
    exit 1
fi

echo ""

# Проверка 2: Содержимое yarn.lock
echo "2. Проверка содержимого yarn.lock:"
first_line=$(head -1 yarn.lock)
if [[ "$first_line" == *"generated"* ]] || [[ "$first_line" == *"yarn"* ]]; then
    echo "   ✓ yarn.lock содержит валидные данные"
else
    echo "   ✗ yarn.lock может быть поврежден!"
fi

echo ""

# Проверка 3: .dockerignore
echo "3. Проверка .dockerignore:"
if [ -f ".dockerignore" ]; then
    if grep -q "^yarn.lock$" .dockerignore; then
        echo "   ✗ ОШИБКА: yarn.lock присутствует в .dockerignore!"
        exit 1
    else
        echo "   ✓ yarn.lock НЕ в .dockerignore"
    fi
    
    if grep -q "^package.json$" .dockerignore; then
        echo "   ✗ ОШИБКА: package.json присутствует в .dockerignore!"
        exit 1
    else
        echo "   ✓ package.json НЕ в .dockerignore"
    fi
else
    echo "   ⚠ .dockerignore не найден"
fi

echo ""

# Проверка 4: .gitignore
echo "4. Проверка .gitignore:"
cd /app
if git check-ignore frontend/yarn.lock 2>/dev/null; then
    echo "   ✗ ОШИБКА: frontend/yarn.lock игнорируется в .gitignore!"
    exit 1
else
    echo "   ✓ frontend/yarn.lock НЕ игнорируется"
fi

echo ""

# Проверка 5: Dockerfile
echo "5. Проверка Dockerfile:"
cd /app/frontend
if [ -f "Dockerfile" ]; then
    if grep -q "COPY package.json" Dockerfile; then
        echo "   ✓ COPY package.json найден в Dockerfile"
    else
        echo "   ⚠ COPY package.json не найден в Dockerfile"
    fi
    
    if grep -q "yarn.lock" Dockerfile; then
        echo "   ✓ yarn.lock упоминается в Dockerfile"
    else
        echo "   ⚠ yarn.lock не упоминается в Dockerfile"
    fi
else
    echo "   ✗ Dockerfile не найден!"
    exit 1
fi

echo ""

# Проверка 6: Симуляция Docker контекста
echo "6. Симуляция Docker build context:"
cd /app/frontend
temp_dir=$(mktemp -d)
echo "   Создан временный каталог: $temp_dir"

# Копируем файлы как Docker
cp package.json "$temp_dir/" 2>/dev/null && echo "   ✓ package.json скопирован" || echo "   ✗ Не удалось скопировать package.json"
cp yarn.lock "$temp_dir/" 2>/dev/null && echo "   ✓ yarn.lock скопирован" || echo "   ✗ Не удалось скопировать yarn.lock"

# Проверяем
if [ -f "$temp_dir/yarn.lock" ]; then
    echo "   ✓ yarn.lock присутствует в симулированном контексте"
else
    echo "   ✗ yarn.lock отсутствует в симулированном контексте!"
fi

rm -rf "$temp_dir"

echo ""
echo "======================================"
echo "Проверка завершена!"
echo "======================================"
echo ""
echo "Если все проверки прошли (✓), можно запускать:"
echo "  docker-compose build frontend"
echo ""
