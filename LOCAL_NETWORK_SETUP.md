# Настройка для работы в локальной сети

## ✅ Изменения для локальной сети

Приложение теперь полностью независимо от hostname и работает в локальной сети без доступа к интернету.

### Что изменено:

**1. Backend CORS - разрешены ВСЕ источники**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**2. Frontend - динамическое определение Backend URL**

Создан файл `/app/frontend/src/config.js`:
```javascript
const getBackendURL = () => {
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8001`;
};
```

Frontend автоматически использует текущий hostname для подключения к backend.

**3. Docker Compose - убраны хардкод URL**

Удалены переменные окружения:
- `CORS_ORIGINS` - больше не нужна
- `REACT_APP_BACKEND_URL` - определяется автоматически

## Доступ к приложению

### В локальной сети

Приложение доступно по любому IP адресу сервера:

```bash
# По IP адресу
http://192.168.1.100:3000

# По hostname
http://my-server:3000
http://my-server.local:3000

# Localhost (на сервере)
http://localhost:3000
```

Backend автоматически будет использовать:
```
http://192.168.1.100:8001
http://my-server:8001
http://localhost:8001
```

### Найти IP адрес сервера

**Linux:**
```bash
# Основной IP
hostname -I | awk '{print $1}'

# Все сетевые интерфейсы
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```powershell
ipconfig | findstr IPv4
```

**macOS:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## Примеры использования

### Сценарий 1: Доступ с другого компьютера

1. **На сервере запущен Docker:**
```bash
cd /app
docker-compose up -d
```

2. **Узнать IP сервера:**
```bash
hostname -I
# Результат: 192.168.1.100
```

3. **С другого компьютера в сети открыть браузер:**
```
http://192.168.1.100:3000
```

Frontend автоматически подключится к `http://192.168.1.100:8001`

### Сценарий 2: Доступ с мобильного устройства

1. Сервер с IP: `192.168.1.100`
2. На телефоне/планшете в той же WiFi сети открыть:
```
http://192.168.1.100:3000
```

### Сценарий 3: Несколько серверов

Можно запустить на разных машинах:

**Сервер 1:** `192.168.1.100:3000`
**Сервер 2:** `192.168.1.101:3000`
**Сервер 3:** `192.168.1.102:3000`

Каждый будет работать независимо с собственной базой данных.

## Настройка фаервола

Откройте порты на сервере:

**Linux (ufw):**
```bash
sudo ufw allow 3000/tcp comment "SecureView Frontend"
sudo ufw allow 8001/tcp comment "SecureView Backend"
sudo ufw reload
```

**Linux (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

**Windows Firewall:**
```powershell
New-NetFirewallRule -DisplayName "SecureView Frontend" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow
New-NetFirewallRule -DisplayName "SecureView Backend" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
```

## Настройка статического IP

Для стабильной работы рекомендуется статический IP.

**Linux (Ubuntu/Debian):**

Отредактируйте `/etc/netplan/01-netcfg.yaml`:
```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

Применить:
```bash
sudo netplan apply
```

## Проверка подключения

### От клиента к серверу

```bash
# Проверить доступность сервера
ping 192.168.1.100

# Проверить порт 3000 (Frontend)
nc -zv 192.168.1.100 3000

# Проверить порт 8001 (Backend)
nc -zv 192.168.1.100 8001

# Проверить через curl
curl http://192.168.1.100:3000
curl http://192.168.1.100:8001/api/stats
```

### Из браузера

Откройте консоль разработчика (F12) и проверьте:

```javascript
// Должно показать текущую конфигурацию
console.log('Backend URL:', window.location.protocol + '//' + window.location.hostname + ':8001');
```

## Работа без DNS

Если нет DNS сервера в локальной сети, используйте:

**Файл hosts (Linux/Mac):**
```bash
sudo nano /etc/hosts

# Добавить
192.168.1.100  secureview
192.168.1.100  secureview.local
```

**Файл hosts (Windows):**
```
C:\Windows\System32\drivers\etc\hosts

# Добавить
192.168.1.100  secureview
192.168.1.100  secureview.local
```

Теперь можно использовать:
```
http://secureview:3000
http://secureview.local:3000
```

## Troubleshooting

### Проблема: "ERR_CONNECTION_REFUSED"

**Причина:** Firewall блокирует порт или Docker не запущен

**Решение:**
```bash
# Проверить Docker
docker-compose ps

# Проверить порты
sudo netstat -tulpn | grep -E "(3000|8001)"

# Открыть порты
sudo ufw allow 3000/tcp
sudo ufw allow 8001/tcp
```

### Проблема: "Failed to fetch" в консоли

**Причина:** Backend недоступен

**Решение:**
```bash
# Проверить backend логи
docker-compose logs backend

# Перезапустить
docker-compose restart backend
```

### Проблема: WebSocket не подключается

**Причина:** Прокси или firewall блокирует WebSocket

**Решение:**
```bash
# Проверить прямое подключение
wscat -c ws://192.168.1.100:8001/api/live/CAMERA_ID

# Если не установлен wscat
npm install -g wscat
```

## Безопасность в локальной сети

### Рекомендации:

1. **Изолированная VLAN** - поместите сервер видеонаблюдения в отдельную VLAN
2. **Нет доступа в интернет** - сервер не должен иметь доступ наружу
3. **VPN для удаленного доступа** - используйте WireGuard или OpenVPN
4. **Резервное копирование** - регулярно делайте backup MongoDB и recordings

### Пример настройки VPN (WireGuard)

Для доступа извне через VPN:

```bash
# Установить WireGuard
sudo apt install wireguard

# После настройки можно подключаться
# из любой точки мира к локальной сети
```

## Мониторинг

Проверить статус системы:

```bash
# CPU/Memory
docker stats

# Дисковое пространство (recordings)
du -sh /app/recordings

# Количество камер и записей
curl http://localhost:8001/api/stats | jq
```

## Резюме

✅ **Работает с любым hostname/IP**
✅ **Не требует интернет**
✅ **CORS разрешен для всех**
✅ **Автоматическое определение backend**
✅ **Готово к использованию в локальной сети**

Просто запустите `docker-compose up -d` и откройте в браузере IP адрес сервера!
