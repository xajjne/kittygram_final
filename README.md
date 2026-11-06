# Kittygram: Docker и GitHub Actions

Kittygram — приложение для публикации фотографий котов и их достижений.
Django REST Framework обслуживает API, React — интерфейс, PostgreSQL 13 —
базу данных. Nginx проксирует `/api/` и `/admin/` в Gunicorn и раздаёт
фронтенд, статику и загруженные изображения.

## Локальный запуск

Требуется запущенный Docker Desktop с Linux-контейнерами и Docker Compose v2+.
Python и Node.js на компьютере устанавливать не нужно: используются Python
3.10 и Node.js 18 внутри контейнеров. Исходные версии учебных зависимостей
сохранены; дополнительно установлен Gunicorn.

```powershell
git clone https://github.com/xajjne/kittygram_final.git
cd kittygram_final
Copy-Item .env.example .env
```

В `.env` замените `POSTGRES_PASSWORD` и `SECRET_KEY` случайными значениями.
Если `.env` уже создан и заполнен, не перезаписывайте его.
В Linux/macOS вместо `Copy-Item` используйте `cp`.

```powershell
docker compose up -d --build
docker compose ps -a
```

Приложение: http://localhost:9000/; админка: http://localhost:9000/admin/.
Миграции и сбор статики Django выполняются при запуске backend.
Первоначальная сборка может занять несколько минут.

```powershell
docker compose exec backend python manage.py createsuperuser
```

Frontend — одноразовый контейнер: он копирует сборку в volume и завершает
работу с кодом 0. Это ожидаемое поведение. Gateway запускается после
копирования фронтенда и успешной проверки готовности backend. Backend
ожидает готовности PostgreSQL.

### Данные и настройки

- `pg_data`: данные PostgreSQL; порт БД наружу не публикуется.
- `static`: сборка React в корне и статика обоих приложений в `static/`.
  Backend пишет в `/app/static/static`, frontend копирует сборку в `/static`,
  gateway читает общий volume из `/static`.
- `media`: backend записывает изображения в `/app/media`, gateway читает
  их из `/media` и отдаёт по `/media/`.

Настройки БД (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`,
`DB_PORT`) и Django (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`) задаются в `.env`.
Этот файл исключён из Git. `ALLOWED_HOSTS` — список имён через запятую без
схемы и порта. По умолчанию `DEBUG=False`.
Изменение пароля в `.env` не меняет пароль уже созданной БД: для существующего
volume пароль нужно менять отдельно в PostgreSQL.

```powershell
docker compose logs --tail=100 backend gateway
docker compose down
```

Обычный `down` сохраняет данные. Не используйте `down -v`, если нужны
существующие коты, фотографии и пользователи.

## Проверки

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test --verbosity 2
docker compose run --rm --no-deps -e CI=true frontend npm test -- --watchAll=false --runInBand
docker compose exec gateway nginx -t
python scripts/smoke_test.py
```

Последняя команда выполняется на компьютере с Python: проверяет сайт,
регистрацию, вход, создание кота и загрузку картинки через gateway.
Тестовая учётная запись и карточка удаляются после проверки.

Ruff проверяет backend с правилами E, F и I. Для отдельной проверки запустите
`ruff check backend` с установленным `ruff==0.9.10`.

В корневом каталоге `tests/` находятся проверки инфраструктуры и внешнего
развёртывания, а тесты самого API — в `backend/cats/tests.py`.
Проверки внешнего развёртывания требуют опубликованных образов и двух
работающих HTTPS-доменов. Когда они будут готовы, скопируйте
`tests.yml.example` в `tests.yml`, укажите реальные адреса и запустите `pytest`
в окружении Python 3.10 с зависимостями из `backend/requirements.txt`.
Примерные домены не предназначены для сдачи проекта.

## GitHub Actions и Docker Hub

Workflow: `.github/workflows/main.yml`. Его точная копия для учебной проверки:
`kittygram_workflow.yml`. При изменении workflow обновляйте оба файла.

На pull request в `main` выполняются проверки без публикации образов.
При push в `main` или ручном запуске workflow из `main`:

1. Ruff проверяет backend; Django проверяет настройки и миграции, запускает
   имеющиеся тесты API с PostgreSQL 13.
2. В отдельной задаче устанавливаются зависимости и запускаются тесты React.
3. Только после успеха обеих задач собираются и публикуются три образа:
   `xajjne/kittygram_backend`, `xajjne/kittygram_frontend`,
   `xajjne/kittygram_gateway`. Каждый получает теги `latest` и SHA коммита.
4. После успешной публикации всех образов отправляется сообщение в Telegram.
   Сообщение подтверждает тестирование и публикацию образов.

В репозитории GitHub откройте **Settings → Secrets and variables → Actions**
и создайте **Repository secrets**:

| Имя | Значение |
| --- | --- |
| `DOCKER_USERNAME` | `xajjne` |
| `DOCKER_PASSWORD` | Docker Hub access token с правом Read & Write |
| `TELEGRAM_TOKEN` | Токен Telegram-бота |
| `TELEGRAM_TO` | ID личного чата или группы |

До первой отправки напишите боту `/start` (для группы добавьте в неё бота).
Секреты не записывайте в файлы репозитория. Образы Docker Hub должны быть
публичными для учебной проверки.

Публикация образов не обновляет уже работающие контейнеры автоматически.
Для запуска опубликованной версии используется отдельный файл без `build`:

```powershell
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d --force-recreate
```

Используйте один выбранный compose-файл для управления запуском.
Смена образа frontend требует повторного запуска его одноразового контейнера;
`--force-recreate` выполняет это и обновляет остальные контейнеры без удаления
volumes.

## Совместная работа с Taski на сервере

Gateway Kittygram публикуется на `127.0.0.1:9000`, поэтому внешний Nginx может
направлять в него запросы по отдельному домену. Конфигурация Taski остаётся
в отдельном virtual host со своим доменом и портом.
Пример для Kittygram: `nginx/host-kittygram.conf.example`.
На сервере задайте настоящий домен, добавьте его в `ALLOWED_HOSTS`, настройте
DNS и HTTPS. Затем проверьте конфигурацию `sudo nginx -t` перед перезагрузкой
Nginx. Этот пример не подключается к контейнерному Nginx автоматически.

Сервер, домены, HTTPS и автоматическое обновление контейнеров по SSH
настраиваются отдельно после предоставления доступа к серверу.
