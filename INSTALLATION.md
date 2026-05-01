# 📦 Инструкция по установке и запуску SPEAR-GUARD

## ⚠️ Docker не обнаружен

Для запуска проекта необходим Docker Desktop.

---

## 🐳 Установка Docker Desktop (Windows)

### Шаг 1: Скачать Docker Desktop

1. Перейдите на официальный сайт: https://www.docker.com/products/docker-desktop/
2. Нажмите **"Download for Windows"**
3. Скачайте установщик `Docker Desktop Installer.exe`

### Шаг 2: Установить Docker Desktop

1. Запустите установщик
2. Следуйте инструкциям мастера установки
3. Убедитесь, что включена опция **"Use WSL 2 instead of Hyper-V"** (рекомендуется)
4. Дождитесь завершения установки
5. **Перезагрузите компьютер** (обязательно!)

### Шаг 3: Запустить Docker Desktop

1. Запустите Docker Desktop из меню Пуск
2. Дождитесь, пока Docker полностью запустится (иконка Docker в трее станет зеленой)
3. Примите лицензионное соглашение при первом запуске

### Шаг 4: Проверить установку

Откройте PowerShell или Git Bash и выполните:

```bash
docker --version
docker-compose --version
```

Вы должны увидеть версии установленных компонентов.

---

## 🚀 Запуск проекта SPEAR-GUARD после установки Docker

### Вариант 1: Через терминал

```bash
# 1. Перейти в директорию проекта
cd "c:\Users\sudxx\OneDrive\Desktop\project"

# 2. Убедиться, что .env файл существует
ls .env

# 3. Запустить все сервисы
docker compose up -d

# 4. Проверить статус сервисов
docker compose ps

# 5. Просмотреть логи
docker compose logs -f backend

# 6. Проверить health endpoint
curl http://localhost:8000/health
```

### Вариант 2: Через Docker Desktop GUI

1. Откройте Docker Desktop
2. Перейдите в раздел **"Containers"**
3. Нажмите на кнопку **"+ Create"** → **"From Compose file"**
4. Выберите файл `docker-compose.yml` из проекта
5. Нажмите **"Start"**

---

## 📊 Проверка работоспособности

После запуска откройте в браузере:

- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc

Ожидаемый ответ `/health`:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000000",
  "services": {
    "redis": "healthy",
    "elasticsearch": "healthy",
    "database": "healthy"
  }
}
```

---

## 🔧 Альтернатива: Локальная установка без Docker

Если по какой-то причине Docker не подходит, можно запустить локально:

### Требования:
- Python 3.11+
- PostgreSQL 15
- Redis 7
- Elasticsearch 8

### Установка сервисов:

#### PostgreSQL
```bash
# Скачать и установить: https://www.postgresql.org/download/windows/
# После установки создать базу данных:
psql -U postgres
CREATE DATABASE spearguard;
```

#### Redis
```bash
# Скачать: https://github.com/microsoftarchive/redis/releases
# Или использовать WSL: wsl -d Ubuntu sudo apt install redis-server
```

#### Elasticsearch
```bash
# Скачать: https://www.elastic.co/downloads/elasticsearch
# Распаковать и запустить bin/elasticsearch.bat
```

### Запуск Backend:

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/spearguard
# REDIS_URL=redis://localhost:6379/0
# ELASTICSEARCH_URL=http://localhost:9200

# Запустить сервер
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🛠️ Устранение неполадок

### Docker не запускается

1. Убедитесь, что виртуализация включена в BIOS
2. Проверьте, что WSL 2 установлен: `wsl --list --verbose`
3. Обновите WSL: `wsl --update`
4. Перезагрузите компьютер

### Порты заняты

Если порты 5432, 6379, 9200, 8000 уже используются:

```bash
# Проверить, что занимает порт
netstat -ano | findstr :8000

# Завершить процесс (замените PID на ID процесса)
taskkill /PID <PID> /F
```

### Ошибки при сборке

```bash
# Очистить кэш Docker
docker system prune -a

# Пересобрать образы
docker compose build --no-cache
docker compose up -d
```

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker compose logs`
2. Проверьте статус: `docker compose ps`
3. Перезапустите сервисы: `docker compose restart`

---

**Следующий шаг**: После успешного запуска Docker, выполните команду:
```bash
docker compose up -d
```
