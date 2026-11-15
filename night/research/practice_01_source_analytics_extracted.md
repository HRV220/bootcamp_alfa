# practice_01_source_analytics.ipynb

## markdown
### Аналитика источников
В этой практике DuckDB используется как локальный аналитический слой для исследования PostgreSQL и MongoDB до загрузки в Lakehouse. 
</br>Цель: увидеть все доступные объекты, выбрать репрезентативные таблицы/коллекции, проверить ключи и связать два источника.

## markdown
### Основные понятия

- **источник** — внешняя система, из которой поступают данные; здесь это PostgreSQL и MongoDB;
- **объект источника** — таблица PostgreSQL или коллекция MongoDB;
- **схема** — логическая область имён объектов, например `dota` или `dota_events`;
- **ключ** — поле, которое идентифицирует запись или связывает записи разных объектов;
- **репрезентативная выборка** — небольшой набор строк для первичного понимания структуры и качества данных;
- **DuckDB** — встраиваемая аналитическая база данных, которая выполняет SQL внутри тетрадки и обращается к внешним источникам через расширения.

В этой практике внешние системы не изменяются. Сначала изучаются объекты и их структура, затем проверяются примеры строк, ключи и возможность объединения. Результаты используются для проектирования RAW-слоя и последующих проверок.

## code
!pip list | grep duckdb

## code
import os

import duckdb

con = duckdb.connect()

pg_dsn = os.environ["DOTA_PG_DSN"]
mongo_uri = os.environ["DOTA_MONGO_URI"]

print(duckdb.__version__)

## markdown
#### Подключение к PostgreSQL:

## code
con.execute("install postgres; load postgres;")
con.execute(f"attach '{pg_dsn}' as pg (type postgres)")

print(con.execute("show databases").fetchall())

## code
print(con.sql("show tables from pg"))

## code
example_postgresql_data = con.execute("""
    select *
    from pg.dota.items
""").fetchone()

print(example_postgresql_data)

## markdown
#### Подключение к MongoDB

## code
con.execute("install mongo from community; load mongo")
con.execute(f"attach '{mongo_uri}' as mongo (type mongo)")

print(con.execute("show databases").fetchall())

## code
print(con.sql("show tables from mongo"))

## code
example_mongodb_data = con.execute("""
    select *
    from mongo.dota_events.gold_events
""").fetchone()

print(example_mongodb_data)

## markdown
#### Спецификация таблицы источника

## code
df = con.execute("describe pg.dota.match_players").df()
print(df[:10])

## markdown
#### Объединение данных для построения аналитики
Основная информация о матчах находится в PostgreSQL и забирается из Steam API, а события по каждому матчу отдельно парсятся и передаются в MongoDB, записывая характеристики события и матч для уникальной идентификации.

Следующий скрипт выводит не более 20 матчей и подсчитывает для каждого количество событий из коллекции `gold_events`:

## markdown
### Как читать запросы DuckDB

После `ATTACH` к объектам обращаются по трёхчастному имени `подключение.схема.объект`. Например, `pg.dota.matches` — таблица `matches` в схеме `dota` подключённой PostgreSQL.

`con.execute(...)` выполняет SQL и возвращает результат. `con.sql(...)` создаёт отношение DuckDB, которое удобно вывести через `.show()`. Метод `.df()` переносит результат в pandas DataFrame. При первичном исследовании выбирайте только нужные поля и ограничивайте объём через `LIMIT`.

Пример профилирования ключа:

```sql
select
    count(*) as rows,
    count(distinct match_id) as distinct_match_ids,
    count(*) filter (where match_id is null) as null_match_ids
from pg.dota.matches;
```

При объединении источников нужно проверить тип и смысл ключа `match_id`. `LEFT JOIN` сохраняет все матчи PostgreSQL и показывает матчи без событий. `INNER JOIN` оставляет только записи, для которых связь найдена в обоих источниках.

## code
con.sql("""
    select m.match_id, m.start_time, m.duration, count(ge.match_id) event_count
    from pg.dota.matches m 
    left join mongo.dota_events.gold_events ge
        on ge.match_id = m.match_id 
    group by all 
    order by event_count desc 
    limit 20
""").show()