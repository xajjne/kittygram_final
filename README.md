# Kittygram: Docker и GitHub Actions

Kittygram — приложение для публикации фотографий котов и их достижений.
Django REST Framework обслуживает API, React — интерфейс, PostgreSQL 13 —
базу данных. Nginx проксирует `/api/` и `/admin/` в Gunicorn и раздаёт
фронтенд, статику и загруженные изображения.

## Цели и возможности проекта

Цель приложения — дать пользователям место для хранения и просмотра
карточек котов: фотографий, основных сведений и достижений. Цель этой
практической работы — обеспечить воспроизводимый запуск приложения
в контейнерах и автоматизировать проверку кода и публикацию образов.

Пользователь может:

- зарегистрироваться, войти в аккаунт и выйти из него;
- просматривать список карточек с постраничной навигацией и отдельную
  карточку кота;
- добавлять кота, указывая имя, цвет, год рождения, фотографию и достижения;
- редактировать и удалять карточки через интерфейс;
- просматривать возраст кота, рассчитанный по году рождения.

Бэкенд предоставляет REST API для пользователей, токенов, котов и достижений.
Администратор управляет учётными записями через панель Django.
Имена пользователей и карточки сохраняются в PostgreSQL, фотографии —
в отдельном Docker volume. Данные сохраняются после пересоздания контейнеров.
GitHub Actions проверяет код и тесты, собирает образы, публикует их
в Docker Hub и отправляет уведомление в Telegram.

## Стек технологий

| Область | Технологии |
| --- | --- |
| Бэкенд | Python 3.10, Django 3.2.3, Django REST Framework 3.12.4 |
| Аутентификация | Djoser 2.1.0, токены DRF |
| База данных | PostgreSQL 13, psycopg2-binary 2.9.3 |
| Изображения и цвета | Pillow 9.0.0, webcolors 1.11.1 |
| Фронтенд | React 17, React Router 5, react-scripts 5, Node.js 18, npm |
| Веб-серверы | Gunicorn 20.1.0, Nginx 1.22.1 |
| Контейнеризация | Docker, Docker Compose |
| Проверки | Ruff, Ruff Format, pycodestyle, pre-commit, Django TestCase, pytest, React Testing Library, Jest |
| Автоматизация | GitHub Actions, Docker Hub, Telegram Bot API |

Зависимости Python перечислены в `backend/requirements.txt`, фронтенда —
в `frontend/package.json` и `frontend/package-lock.json`.

## Локальный запуск

Требуются Git, запущенный Docker Desktop с Linux-контейнерами
и Docker Compose v2+. Порт `9000` на компьютере должен быть свободен.
Python и Node.js на компьютере устанавливать не нужно: используются Python
3.10 и Node.js 18 внутри контейнеров. Исходные версии учебных зависимостей
сохранены; дополнительно установлен Gunicorn.

```powershell
git clone https://github.com/xajjne/kittygram_final.git
cd kittygram_final
Copy-Item .env.example .env
```

### Заполнение .env

Файл `.env` должен находиться в корне проекта рядом с `docker-compose.yml`.
Откройте скопированный файл в текстовом редакторе. Пример его структуры:

```dotenv
POSTGRES_DB=kittygram
POSTGRES_USER=kittygram
POSTGRES_PASSWORD=replace-with-a-random-password
DB_HOST=db
DB_PORT=5432
SECRET_KEY=replace-with-a-random-django-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,backend
```

| Переменная | Как заполнить |
| --- | --- |
| `POSTGRES_DB` | Имя создаваемой БД; для локального запуска оставьте `kittygram`. |
| `POSTGRES_USER` | Пользователь PostgreSQL; можно оставить `kittygram`. |
| `POSTGRES_PASSWORD` | Замените пример длинным случайным паролем БД. |
| `DB_HOST` | Оставьте `db`: это имя сервиса PostgreSQL в Compose. |
| `DB_PORT` | Оставьте `5432`: внутренний порт PostgreSQL. |
| `SECRET_KEY` | Замените пример отдельной длинной случайной строкой для Django. |
| `DEBUG` | Оставьте `False`; не включайте отладку на публичном сервере. |
| `ALLOWED_HOSTS` | Для localhost оставьте пример; для сервера добавьте его домен или IP. |

Для пароля БД и ключа Django используйте разные значения, например
сгенерированные менеджером паролей. Не оставляйте строки `replace-with-...`.
`ALLOWED_HOSTS` содержит имена через запятую, без `http://`, `https://`, путей
и портов. Имя `backend` нужно для обращений внутри сети контейнеров.
Compose передаёт значения из `.env` контейнерам `db` и `backend`, Django
читает их из переменных окружения. Содержимое `.env` не публикуется в Git.

Если `.env` уже создан и заполнен, не перезаписывайте его.
В Linux/macOS вместо `Copy-Item` используйте `cp`.

### Сборка и запуск

Выполняйте команды из корня проекта:

```powershell
docker compose config --quiet
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

Ruff проверяет Python-код с правилами E, F и I, Ruff Format — форматирование,
pycodestyle — соответствие PEP 8. Версии инструментов зафиксированы
в `requirements-dev.txt`.

### Автоматические проверки перед коммитом

Для инструментов разработки создайте отдельное окружение Python 3.9+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
```

В Linux/macOS активируйте окружение командой `source .venv/bin/activate`.
Это окружение содержит инструменты разработки; само приложение по-прежнему
работает внутри Docker. После клонирования репозитория команду
`pre-commit install` нужно выполнить на каждом компьютере отдельно.

Перед каждым коммитом hooks автоматически исправляют доступные Ruff ошибки,
форматируют изменённые Python-файлы и запускают pycodestyle.
Если hook изменил файл, проверьте изменения, выполните `git add` и повторите
коммит. Если проверка стиля не прошла, сначала исправьте её замечания.
Сгенерированные миграции исключены из форматирования и проверок стиля.
CI использует те же версии инструментов, но только проверяет файлы.

Проверки можно выполнить по отдельности:

```powershell
ruff check backend scripts
ruff format --check backend scripts
pycodestyle backend scripts
```

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

При push в любую ветку запускаются Ruff, Ruff Format, pycodestyle
и тесты бэкенда и фронтенда.
На pull request в `main`/`master` и при ручном запуске выполняются проверки
без публикации образов. Публикация разрешена только при push в `main` или
`master` после успешных проверок:

1. В параллельной матрице Python 3.9 и 3.10 проверяются стиль и форматирование,
   настройки Django и миграции; запускаются имеющиеся тесты API с PostgreSQL 13.
   Эти версии выбраны для существующих учебных зависимостей Django 3.2,
   Pillow 9 и psycopg2-binary 2.9.3. Добавление Python 3.11/3.12 требует
   отдельного обновления зависимостей и проверки совместимости.
2. В отдельной задаче устанавливаются зависимости и запускаются тесты React.
3. Только после успеха обеих задач собираются и публикуются три образа:
   `<DOCKER_USERNAME>/kittygram_backend`, `<DOCKER_USERNAME>/kittygram_frontend`,
   `<DOCKER_USERNAME>/kittygram_gateway`. Логин берётся из секрета
   `DOCKER_USERNAME`. Каждый образ получает теги `latest` и SHA коммита.
4. После успешной публикации всех образов отправляется сообщение в Telegram.
   Сообщение подтверждает тестирование и публикацию образов, содержит автора
   пуша, сообщение последнего коммита и ссылки на коммит и запуск workflow.

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
