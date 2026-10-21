# Лабораторная работа № 2 — знакомство с Docker

**Дисциплина:** «Контейнеризация и оркестрация приложений».

**Студент:** Андреев Александр · **ИСУ:** 464998 · **Группа:** К3320.

**Порт:** 5528 · **Префикс:** `andreev` · **Образ:** `andreev-assistant`.

Цель работы — собрать образ FastAPI-приложения, уменьшить его размер,
настроить исключения контекста сборки и HEALTHCHECK, затем присвоить
финальному образу семантический и датированный теги.

## Файлы проекта

| Файл | Назначение |
| --- | --- |
| `app/main.py` | Исходное приложение: персонализация, заметки, погода и проверка ключа |
| `requirements.txt` | Зависимости FastAPI, Uvicorn и HTTPX |
| `Dockerfile` | Первоначальная сборка v1; используется также для v3 |
| `Dockerfile.optimized.v2` | Multi-stage сборка v2 без curl и HEALTHCHECK |
| `Dockerfile.optimized` | Финальная multi-stage сборка с curl и HEALTHCHECK |
| `.dockerignore` | Исключения контекста сборки из выполненной лабораторной |
| `.gitignore` | Исключение локальных окружений, настроек и кэша из Git |

## Сборка и запуск

Команды рассчитаны на Bash в Linux с работающим Docker Engine.

```bash
git clone https://github.com/alx-an/docker-lab2.git
cd docker-lab2

docker build -t andreev-assistant:v1 .
docker build -t andreev-assistant:v2 -f Dockerfile.optimized.v2 .
docker build -t andreev-assistant:v3 .
docker build -t andreev-assistant:final -f Dockerfile.optimized .
docker images --filter 'reference=andreev-assistant:*'
```

В лабораторной v2 собирался из промежуточного `Dockerfile.optimized`.
Здесь этот вариант сохранён отдельно в `Dockerfile.optimized.v2`.
v3 собирается из обычного `Dockerfile` после добавления `.dockerignore`.

Перед запуском освободите порт 5528. Задайте свой учебный ключ из латинских
букв и цифр: ввод скрыт, значение передаётся контейнеру через окружение.

```bash
read -rsp 'Учебный APP_SECRET: ' APP_SECRET
printf '\n'
export APP_SECRET
: "${APP_SECRET:?Нужно задать непустой учебный ключ}"

docker run -d \
  --name andreev-assistant-final \
  -p 5528:5528 \
  -e APP_OWNER=andreev \
  -e APP_SECRET \
  andreev-assistant:final
```

## Проверка приложения

```bash
curl -fsS http://localhost:5528/
curl -fsS http://localhost:5528/me
curl -fsS -X POST http://localhost:5528/notes \
  -H 'Content-Type: application/json' \
  -d '{"text":"ЛР2: сборка образа"}'
curl -fsS http://localhost:5528/notes
curl -fsS "http://localhost:5528/secret/${APP_SECRET}"
```

`/me` возвращает владельца `andreev`, а правильный ключ — флаг
`LAB2_SUCCESS_ANDREEV`. Заметки хранятся в памяти процесса и теряются при
перезапуске. В приложении также есть `/docs` и `/weather/{city}`;
погодный эндпоинт обращается к внешнему API Open-Meteo.

## HEALTHCHECK

```bash
sleep 40
docker ps --filter 'name=andreev-assistant-final' \
  --format 'table {{.Names}}\t{{.Status}}'
docker inspect --format '{{.State.Health.Status}}' andreev-assistant-final
curl -fsS http://localhost:5528/health
```

Ожидаемый статус — `healthy`, ответ `/health`:
`{"status":"healthy","owner":"andreev"}`.
Проверка выполняется через curl внутри контейнера: интервал 30 с,
таймаут 5 с, стартовый период 10 с, порог — 3 последовательные неудачи.

## Тегирование

```bash
docker tag andreev-assistant:final andreev-assistant:1.0.0
docker tag andreev-assistant:final "andreev-assistant:$(date +%Y%m%d)"
docker image ls --filter 'reference=andreev-assistant:*' \
  --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}'
```

## Результаты лабораторной

Данные зафиксированы **21.10.2026** в виртуальной машине `Ubuntu-Lab`.

| Версия | Размер | IMAGE ID |
| --- | --- | --- |
| v1 | 188 MB | `991432084f66` |
| v2 | 164 MB | `c6fd5da2c875` |
| v3 | 188 MB | `991432084f66` |
| final | 178 MB | `9c31d93b1da8` |

Оптимизация v1 → v2: **−24 MB (12,8%)**. HEALTHCHECK: **healthy**.
Получен персональный флаг **LAB2_SUCCESS_ANDREEV**.

`--no-cache-dir` отключает кэш pip, а multi-stage сборка переносит зависимости
из builder в среду выполнения. Отдельное копирование `requirements.txt`
позволяет переиспользовать слой установки зависимостей при изменении `app/`.
Добавление curl увеличило размер final относительно v2 на 14 MB.

v1 и v3 имеют одинаковый IMAGE ID: содержимое образа не изменилось,
слои были взяты из кэша. Теги `final`, `1.0.0` и `20261021` указывают
на один образ размером 178 MB. При повторной сборке размеры и идентификаторы
могут отличаться из-за обновлений базового образа и транзитивных зависимостей.

## Источник и авторство

Исходное приложение: [FilBTi/assist-py](https://github.com/FilBTi/assist-py),
коммит [`a5af30e`](https://github.com/FilBTi/assist-py/commit/a5af30e52388b3ab36db5dfde939ce3eef0c3df4).
Автор исходного коммита — **fil**; история Git сохранена.
Код `app/main.py` и зависимости оставлены без изменений.
Конфигурация Docker и описание лабораторной подготовлены Андреевым Александром.

В исходном репозитории отдельная лицензия не указана.
Этот fork не устанавливает новую лицензию на исходный код.
