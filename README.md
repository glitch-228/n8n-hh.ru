# HH.ru Automation

Автоматизация поиска и откликов на вакансии HH.ru через Python + n8n + Google Gemini AI.

### Ссылка на видео с гайдом: https://www.youtube.com/watch?v=EakL7eoSL9U

## Установка

### 1. Создание виртуального окружения

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install playwright python-dotenv
playwright install chromium
```

### 3. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
# Путь к директории n8n (обязательно укажите свой путь)
N8N_FILES_DIR=/Users/your_username/.n8n-files

# Настройки сервера
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# Настройки поиска
DEFAULT_SEARCH_TEXT=Frontend
AREA_CODE=113
```

**Важно:** Замените `/Users/your_username/.n8n-files` на реальный путь к вашей директории n8n.

## Запуск

### 1. Авторизация на HH.ru

Перед первым использованием необходимо сохранить сессию:

```bash
source .venv/bin/activate
python hh_login.py
```

Откроется браузер. Войдите в аккаунт HH.ru, дождитесь полной загрузки личного кабинета, затем нажмите Enter в терминале.

### 2. Запуск сервера

```bash
source .venv/bin/activate
python hh_server.py
```

Сервер запустится на `http://127.0.0.1:8000`.

### 3. Настройка n8n

1. Импортируйте workflow из файла `HH.ru Flow (With AI and Pagination).json`
2. Добавьте Google Gemini API credentials в n8n (Settings → Credentials)
3. Запустите workflow

## API Endpoints

### GET /search

Поиск вакансий.

**Параметры:**
- `text` - поисковый запрос (по умолчанию: "Frontend")
- `page` - номер страницы (по умолчанию: 0)

**Пример:**
```bash
curl "http://127.0.0.1:8000/search?text=Python&page=0"
```

### POST /apply

Отклик на вакансию.

**Body:**
```json
{
  "url": "https://hh.ru/vacancy/123456",
  "message": "Текст сопроводительного письма"
}
```

**Пример:**
```bash
curl -X POST http://127.0.0.1:8000/apply \
  -H "Content-Type: application/json" \
  -d '{"url": "https://hh.ru/vacancy/123456", "message": "Здравствуйте..."}'
```

## Структура проекта

```
.
├── hh_server.py          # HTTP сервер с API
├── hh_login.py           # Скрипт авторизации
├── search_vacancies.py   # Логика поиска вакансий
├── apply_vacancy.py      # Логика отклика на вакансии
├── .env                  # Конфигурация (создать вручную)
└── HH.ru Flow (With AI and Pagination).json  # n8n workflow
```

## Troubleshooting

### Session file not found

Запустите `python hh_login.py` для создания файла сессии.

### Playwright browser not found

```bash
playwright install chromium
```

### Неверный путь N8N_FILES_DIR

Проверьте, что путь в `.env` существует и доступен для записи. Создайте директорию вручную:

```bash
mkdir -p /path/to/.n8n-files
```

## Ограничения

- Базовый синхронный HTTP сервер (не для production)
- Синхронный Playwright (блокирует поток на время выполнения)
- Нет обработки rate limiting от HH.ru
- Требуется периодическое обновление сессии

## Google Gemini API

Получите API ключ: [Google AI Studio](https://makersuite.google.com/app/apikey)

Бесплатный tier: 60 запросов/минуту (достаточно для автоматизации).

## Рекомендации

1. Не превышайте 3-5 страниц за один запуск (60-100 вакансий)
2. Используйте задержки между откликами (минимум 5 секунд)
3. Обновляйте сессию раз в неделю через `hh_login.py`
4. Мониторьте статистику откликов в личном кабинете HH.ru
