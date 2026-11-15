# practice_03_stage.ipynb

## markdown
### Stage: типизация, очистка и объединения
Этот слой уже нужен для преподготовки данных к аналитической работе, здесь данные преобразуются к чистому, широкому виду.

Построим воспроизводимый STAGE из RAW: нормализуем типы, восстановим временную метку события, уберём технический шум. Каждая запись результата сопровождается OpenLineage run в пространстве `jh`.

## markdown
### Как работает OpenLineage

`ctx.lineage(...)` описывает одну операцию преобразования данных и отправляет её в OpenLineage/Marquez. При входе в блок отправляется событие `START`. Если код завершился успешно, отправляется `COMPLETE`; если возникло исключение — `FAIL` с текстом ошибки. Само исключение не скрывается и продолжает отображаться в notebook.

Блок lineage должен охватывать именно чтение, преобразование и запись результата:

```python
with ctx.lineage(
    'job-name',
    inputs=['raw.source_table'],
    output='stage.result_table',
    description='Что делает преобразование',
    columns={'result_id': 'raw.source_table.source_id'},
    config={'filter': 'source_id is not null'},
):
    result = spark.table('lakehouse.raw.source_table')
    result.writeTo('lakehouse.stage.result_table').using('iceberg').createOrReplace()
```

Параметры короткой спецификации:

- первый аргумент — стабильное имя операции, по которому запуски группируются в UI;
- `inputs` — входные datasets в формате `слой.таблица`; сокращённое имя `raw.<таблица>` автоматически указывает на канонический объект `lakehouse_raw / lakehouse.raw.<таблица>`;
- `output` — один выходной dataset; для нескольких результатов можно использовать `outputs`;
- `description` — назначение преобразования;
- `dataset_descriptions` — необязательные описания datasets; обычно здесь достаточно описать создаваемый результат, потому что входные таблицы уже документированы в Iceberg;
- `columns` — происхождение выходных колонок. Для прямого переноса указывается одна строка `dataset.column`, для вычисляемой колонки — список всех исходных полей;
- `config` — важные правила преобразования: join, filter, формулы, удалённые поля и другие параметры.

Helper выполняет `describe table extended` для каждого входного и выходного объекта Iceberg. Из результата автоматически передаются схема, типы и комментарии полей, расположение, поставщик данных и описание таблицы. Комментарии полей хранятся только в схеме и не дублируются в описании объекта. Явное значение из `dataset_descriptions` переопределяет описание таблицы.

Объекты RAW не копируются в пространство Jupyter: `raw.pg__matches` в `inputs` и `columns` преобразуется в `lakehouse_raw / lakehouse.raw.pg__matches`. Результаты `stage.*` создаются в `jh_stage`, а `mart.*` — в `jh_mart`. Поэтому lineage строится напрямую как `lakehouse_raw -> jh_stage/stage`, без промежуточного RAW-дубликата. В `columns` нужно описывать бизнес-значимые связи, а в `config` — правила, которые невозможно однозначно восстановить только из схемы. Имена должны совпадать с фактическими таблицами и колонками Spark-кода.

## markdown
### Что происходит в слое STAGE

STAGE — слой подготовленных данных между RAW и витринами. В RAW сохраняется форма источника, а в STAGE мы приводим типы к удобному виду, отбрасываем явно неподходящие записи, добавляем производные поля и объединяем связанные источники.

Для каждой операции фиксируем допустимые записи, ключи, формулы новых полей, уровень детализации и технические поля загрузки. Это делает преобразование воспроизводимым и позволяет объяснить происхождение каждой колонки.

Один и тот же отбор можно выразить через DataFrame API или Spark SQL. DataFrame API удобен для пошаговой сборки выражения и функций Python. SQL удобен для явного описания правила, которое легко прочитать и проверить отдельно. Ниже сначала выполняется вариант через DataFrame API, затем приводится SQL-эквивалент без повторной записи таблицы.

## code
from lakehouse_spark import SparkSessionContext
from lakehouse_publish import publish_table
from pyspark.sql import functions as F

## code
with SparkSessionContext('jh-stage-transform') as ctx:
    spark = ctx
    with ctx.lineage(
        'build-stage-matches', 
        inputs=['raw.pg__matches'],
        output='stage.practice_matches',
        description='Типизация и очистка матчей из RAW PostgreSQL для STAGE-слоя',
        dataset_descriptions={
            'stage.practice_matches': 'Очищенные и типизированные матчи для аналитических преобразований',
        },
        columns={
            'match_id': 'raw.pg__matches.match_id',
            'duration': 'raw.pg__matches.duration',
            'radiant_win': 'raw.pg__matches.radiant_win',
            'human_players': 'raw.pg__matches.human_players',
            'game_mode': 'raw.pg__matches.game_mode',
            'started_at': 'raw.pg__matches.start_time',
            'source_loaded_at': 'raw.pg__matches.sys_insert_stamp',
        },
        config={
            'filter': 'match_id is not null and start_time is not null and duration >= 0',
            'started_at': 'to_timestamp(from_unixtime(start_time))',
            'dropped_columns': ['start_time', 'sys_insert_stamp'],
        }
    ):
        matches = (
            spark
                .table('lakehouse.raw.pg__matches')
                .select('match_id', 'start_time', 'duration',
                        'radiant_win', 'human_players', 
                        'game_mode','sys_insert_stamp')
                .where('match_id is not null and start_time is not null and duration >= 0')
                .withColumn('started_at', F.to_timestamp(F.from_unixtime('start_time')))
                .withColumn('source_loaded_at', F.col('sys_insert_stamp'))
                .withColumn('stage_loaded_at', F.current_timestamp())
                .drop('start_time','sys_insert_stamp')
        )
        matches.writeTo('lakehouse.stage.practice_matches').using('iceberg').createOrReplace()
        publish_table('stage', 'practice_matches', matches, description='Очищенные и типизированные матчи для аналитических преобразований', dependencies=['raw/pg__matches'])
    spark.table('lakehouse.stage.practice_matches').printSchema()
    spark.table('lakehouse.stage.practice_matches').show(10, False)


## code
with SparkSessionContext('jh-stage-events') as ctx:
    spark = ctx
    with ctx.lineage(
        'build-stage-kill-events', 
        inputs=['raw.mongo__kill_events', 'stage.practice_matches'],
        output='stage.practice_kill_events',
        description='Обогащение событий убийств временем начала матча в STAGE-слое',
        dataset_descriptions={
            'stage.practice_kill_events': 'События убийств, обогащенные временем события',
        },
        columns={
            'id': 'raw.mongo__kill_events.id',
            'match_id': 'raw.mongo__kill_events.match_id',
            'attacker': 'raw.mongo__kill_events.attacker',
            'target': 'raw.mongo__kill_events.target',
            'time': 'raw.mongo__kill_events.time',
            'started_at': 'stage.practice_matches.started_at',
            'event_at': [
                'stage.practice_matches.started_at',
                'raw.mongo__kill_events.time',
            ],
            'sys_insert_stamp': 'raw.mongo__kill_events.sys_insert_stamp',
        },
        config={
            'join': 'raw.mongo__kill_events.match_id = stage.practice_matches.match_id',
            'filter': 'id is not null and time >= 0',
            'event_at': 'started_at + time seconds',
        }
    ):
        events = (
            spark.table('lakehouse.raw.mongo__kill_events').alias('e')
                .join(spark.table('lakehouse.stage.practice_matches').alias('m'), 'match_id')
                .select('e.id','e.match_id','e.attacker','e.target','e.time','m.started_at','e.sys_insert_stamp')
                .withColumn('event_at', F.expr('started_at + make_interval(0, 0, 0, 0, 0, 0, time)'))
                .withColumn('stage_loaded_at', F.current_timestamp())
                .where('id is not null and time >= 0')
        )
        events.writeTo('lakehouse.stage.practice_kill_events').using('iceberg').createOrReplace()
        publish_table('stage', 'practice_kill_events', events, description='События убийств, обогащенные временем события', dependencies=['raw/mongo__kill_events', 'stage/practice_matches'])
    (
        spark
            .table('lakehouse.stage.practice_kill_events')
            .selectExpr(
                'count(*) rows',
                'count(distinct id) event_ids',
                'min(event_at)','max(event_at)'
            ).show()
    )

## markdown
### Эквивалент преобразования через Spark SQL

Эта демонстрационная ячейка строит тот же результат в памяти и не записывает вторую таблицу. Сравните схему, фильтр и вычисление `started_at` с предыдущей ячейкой. В рабочем процессе выбирайте один основной способ записи результата, чтобы не создавать конкурирующие версии одной таблицы.

## code
with SparkSessionContext('jh-stage-transform-sql') as ctx:
    spark = ctx
    matches_sql = spark.sql('''
        select
            match_id,
            duration,
            radiant_win,
            human_players,
            game_mode,
            to_timestamp(from_unixtime(start_time)) as started_at,
            sys_insert_stamp as source_loaded_at,
            current_timestamp() as stage_loaded_at
        from lakehouse.raw.pg__matches
        where match_id is not null
          and start_time is not null
          and duration >= 0
    ''')
    matches_sql.printSchema()
    matches_sql.show(10, truncate=False)