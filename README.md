# Лабораторная работа № 3 — персистентность и изоляция

**Дисциплина:** «Контейнеризация и оркестрация приложений».
**Студент:** Андреев Александр · **ИСУ:** 464998 · **Группа:** К3320.

Приложение FastAPI сохраняет заметки в PostgreSQL 15. Данные БД находятся
в томе `andreev-pgdata`, конфигурация подключается через Bind Mount,
контейнеры взаимодействуют в сети `andreev-backend`.

## Структура

- `solutions/assist-py/app/` — приложение, подключение к БД, модель и CRUD.
- `solutions/assist-py/requirements.txt` — зависимости, включая SQLAlchemy и psycopg2-binary.
- `solutions/assist-py/Dockerfile` — сборка ЛР3, порт 8098.
- `solutions/assist-py/config/app.conf` — конфигурация без паролей.
- `solutions/reports/lab-3/` — [DOCX](solutions/reports/lab-3/ЛР3_Андреев_АА_464998.docx) и [PDF](solutions/reports/lab-3/ЛР3_Андреев_АА_464998.pdf).

`Dockerfile.optimized` и `Dockerfile.optimized.v2` сохранены как варианты ЛР2
с портом 5528. Для ЛР3 используется обычный `Dockerfile`.
Предыдущая работа находится в [ветке lab-2](https://github.com/alx-an/docker-lab2/tree/lab-2).

## Подготовка

Команды рассчитаны на Bash в Ubuntu с Docker Engine, curl и Python 3.
Выполняйте этапы последовательно в одной оболочке из каталога приложения.
Перед первым запуском имена контейнеров и порты 5528 и 8098 должны быть свободны.

```bash
git clone --branch lab-3 https://github.com/alx-an/docker-lab2.git
cd docker-lab2/solutions/assist-py
docker build -t andreev-assistant:v3 .

read -rsp 'Учебный пароль PostgreSQL: ' POSTGRES_PASSWORD
printf '\n'
read -rsp 'Учебный APP_SECRET: ' APP_SECRET
printf '\n'
export POSTGRES_PASSWORD APP_SECRET
: "${POSTGRES_PASSWORD:?Нужен непустой пароль}"
: "${APP_SECRET:?Нужен непустой ключ}"
DB_PASSWORD_URL=$(python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["POSTGRES_PASSWORD"], safe=""))')
export DATABASE_URL="postgresql://user_98:${DB_PASSWORD_URL}@host.docker.internal:5528/andreev98"
```

Для существующего тома вводится пароль, с которым база была инициализирована.
Переменные `POSTGRES_*` создают пользователя и БД только в пустом каталоге данных;
смена переменной не меняет пароль в уже созданной базе.

## Хранение данных

### 1. Именованный том и PostgreSQL

```bash
docker volume create andreev-pgdata
docker volume ls --filter 'name=andreev-pgdata'
docker volume inspect andreev-pgdata
docker run -d --name andreev-postgres \
  -e POSTGRES_USER=user_98 -e POSTGRES_PASSWORD \
  -e POSTGRES_DB=andreev98 \
  -v andreev-pgdata:/var/lib/postgresql/data \
  -p 5528:5432 postgres:15
until docker exec andreev-postgres pg_isready -U user_98 -d andreev98; do
  sleep 1
done
docker run -d --name andreev-assistant \
  -p 8098:8098 -e APP_OWNER=andreev -e APP_SECRET \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL andreev-assistant:v3
until curl -fsS http://localhost:8098/health; do sleep 1; done
curl -fsS http://localhost:8098/
curl -fsS http://localhost:8098/health
curl -fsS -X POST http://localhost:8098/notes \
  -H 'Content-Type: application/json' \
  -d '{"text":"ЛР3: данные в БД"}'
curl -fsS http://localhost:8098/notes
docker exec andreev-postgres psql -U user_98 -d andreev98 \
  -c 'SELECT id, owner, text FROM notes;'
```

`database.py` создаёт подключение и сессии SQLAlchemy, `models.py` описывает
таблицу `notes`, `crud.py` выполняет операции с данными. `GET /notes` выбирает
записи владельца `andreev`. `/health` возвращает статус API без запроса к БД:
работу базы подтверждают создание и чтение заметок и SQL-запрос.

### 2. Сохранность при пересоздании приложения

```bash
curl -fsS http://localhost:8098/notes
docker stop andreev-assistant
docker rm andreev-assistant
docker run -d --name andreev-assistant \
  -p 8098:8098 -e APP_OWNER=andreev -e APP_SECRET \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL andreev-assistant:v3
until curl -fsS http://localhost:8098/health; do sleep 1; done
curl -fsS http://localhost:8098/notes | python3 -m json.tool
```

Прежняя заметка остаётся доступной. PostgreSQL и его том на этом этапе
не удаляются. Именованный том не удаляется вместе с контейнером.

### 3. Bind Mount для конфигурации

В репозитории сохранено конечное значение `maintenance_mode=true`.
Для повторения опыта от исходного состояния:

```bash
sed -i 's/^maintenance_mode=.*/maintenance_mode=false/' config/app.conf
docker stop andreev-assistant
docker rm andreev-assistant
docker run -d --name andreev-assistant-config \
  -p 8098:8098 -e APP_OWNER=andreev -e APP_SECRET \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL \
  -v "$(pwd)/config:/app/config:ro" andreev-assistant:v3
docker exec -it andreev-assistant-config sh
```

В оболочке контейнера:

```sh
cat /app/config/app.conf
exit
```

Снова на хосте:

```bash
sed -i 's/^maintenance_mode=false/maintenance_mode=true/' config/app.conf
docker restart andreev-assistant-config
docker exec andreev-assistant-config cat /app/config/app.conf
```

`$(pwd)/config` — каталог Ubuntu, `/app/config` — путь в контейнере,
`ro` — доступ только для чтения из контейнера. Изменение видно без пересборки
образа. Опыт проверяет монтирование файла; логика режима обслуживания
в API не реализована. Volume управляется Docker, Bind Mount связан с путём хоста.

### 4. Пользовательская сеть

```bash
docker network create andreev-backend
docker stop andreev-postgres andreev-assistant-config
docker rm andreev-postgres andreev-assistant-config
docker run -d --name andreev-postgres --network andreev-backend \
  -e POSTGRES_USER=user_98 -e POSTGRES_PASSWORD \
  -e POSTGRES_DB=andreev98 \
  -v andreev-pgdata:/var/lib/postgresql/data postgres:15
until docker exec andreev-postgres pg_isready -U user_98 -d andreev98; do
  sleep 1
done
export DATABASE_URL="postgresql://user_98:${DB_PASSWORD_URL}@andreev-postgres:5432/andreev98"
docker run -d --name andreev-assistant --network andreev-backend \
  -p 8098:8098 -e APP_OWNER=andreev -e APP_SECRET -e DATABASE_URL \
  -v "$(pwd)/config:/app/config:ro" andreev-assistant:v3
until curl -fsS http://localhost:8098/health; do sleep 1; done
curl -fsS http://localhost:8098/notes
curl -fsS -X POST http://localhost:8098/notes \
  -H 'Content-Type: application/json' \
  -d '{"text":"ЛР3: сеть работает!"}'
curl -fsS http://localhost:8098/notes
docker run --rm alpine:3.18 ping -c 2 andreev-postgres
docker run --rm --network andreev-backend \
  alpine:3.18 ping -c 2 andreev-postgres
docker network inspect andreev-backend \
  --format '{{range .Containers}}{{.Name}} {{end}}'
```

Первый `ping` ожидаемо завершается ошибкой `bad address`; второй получает ответы.
Это проверка разрешения имени и связи внутри сети, а не доказательство абсолютной
недоступности БД извне. В общей сети имя `andreev-postgres` разрешает Docker DNS.
PostgreSQL использует прежний том и больше не публикует порт на хосте.

При однократном прохождении на пустой базе результат — две заметки. Повторные
POST добавляют записи, поэтому `count` может быть больше двух.

### 5. Итоговая проверка

```bash
date '+%d.%m.%Y %H:%M:%S'
printf '%s@%s\n' "$(whoami)" "$(hostname)"
docker ps --filter 'name=andreev-' \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker volume ls --filter 'name=andreev-'
docker network ls --filter 'name=andreev-'
```

В практической работе 03.11.2026 в 20:01:11 зафиксированы два работающих
контейнера, том `andreev-pgdata` (`local`) и сеть `andreev-backend` (`bridge`,
область `local`). Порт приложения — `8098→8098/tcp`, PostgreSQL — внутренний
`5432/tcp` без публикации. Семь исходных скриншотов включены в отчёт.

## Источник и авторство

Исходное приложение: [FilBTi/assist-py](https://github.com/FilBTi/assist-py),
коммит [`a5af30e`](https://github.com/FilBTi/assist-py/commit/a5af30e52388b3ab36db5dfde939ce3eef0c3df4).
Автор исходного коммита — **fil**; история Git сохранена.
В ЛР3 приложение и зависимости дополнены поддержкой PostgreSQL.
Конфигурация Docker и описание лабораторной подготовлены Андреевым Александром.

В исходном репозитории отдельная лицензия не указана.
Этот fork не устанавливает новую лицензию на исходный код.
