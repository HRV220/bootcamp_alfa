# practice_04_mart.ipynb

## markdown
# 4. MART: бизнес-модель и агрегаты
Соберём несколько витрин с разной гранулярностью: дневную сводку матчей, профиль героя или режима и аналитику событий. Для каждой таблицы определим потребителя, уровень детализации, метрики, актуальность данных и правила обновления.

## markdown
## Как устроена витрина

Витрина — это таблица, подготовленная под конкретный аналитический вопрос или потребителя. В отличие от RAW и STAGE, она не просто сохраняет или очищает данные, а фиксирует удобную бизнес-модель: понятные показатели, уровень детализации и правила расчёта.

Перед созданием витрины нужно определить:

- **потребителя** — кто будет использовать таблицу;
- **уровень детализации** — что означает одна строка; например, один день или одна пара «дата и атакующий»;
- **метрики** — какие показатели рассчитываются и в каких единицах;
- **период данных** — за какой промежуток можно делать выводы;
- **актуальность** — насколько свежими должны быть данные;
- **правила обновления** — полная пересборка, добавление новых строк или изменение существующих.

В этой тетрадке `practice_match_daily` содержит одну строку на день матча. `practice_kill_summary` содержит одну строку на сочетание даты события и атакующего. Эти определения нужно проверить до написания SQL: от них зависят группировка, интерпретация показателей и отсутствие двойного счёта.

Каждое построение витрины оборачивается в `ctx.lineage(...)`. Источники STAGE отображаются в `jh_stage`, результаты MART — в `jh_mart`, а RAW остаётся в каноническом `lakehouse_raw`. В описании указываются источники, результат и правила расчёта, чтобы в Marquez можно было восстановить происхождение показателей. Поля `inputs`, `output`, `description`, `columns` и `config` описаны в тетрадке `practice_03_stage`.

## code
from lakehouse_spark import SparkSessionContext
from lakehouse_publish import publish_table
from pyspark.sql import functions as F
with SparkSessionContext('jh-mart-matches') as ctx:
    spark = ctx
    with ctx.lineage(
        'build-mart-match-daily',
        inputs=['stage.practice_matches'],
        output='mart.practice_match_daily',
        description='Ежедневная витрина матчей с длительностью и долей побед Radiant',
        dataset_descriptions={
            'stage.practice_matches': 'Очищенные и типизированные матчи STAGE-слоя',
            'mart.practice_match_daily': 'Одна строка на дату матча с основными показателями',
        },
        columns={
            'match_date': 'stage.practice_matches.started_at',
            'matches': 'stage.practice_matches.match_id',
            'avg_duration_seconds': 'stage.practice_matches.duration',
            'radiant_win_rate': 'stage.practice_matches.radiant_win',
            'game_modes': 'stage.practice_matches.game_mode',
        },
        config={
            'grain': 'one row per match_date',
            'group_by': 'to_date(started_at)',
            'metrics': ['count(*)', 'avg(duration)', 'avg(radiant_win)', 'countDistinct(game_mode)'],
        }
    ):
        daily = (
            spark.table('lakehouse.stage.practice_matches')
                .groupBy(F.to_date('started_at').alias('match_date'))
                .agg(
                    F.count('*').alias('matches'), 
                    F.avg('duration').alias('avg_duration_seconds'), 
                    F.expr('avg(case when radiant_win then 1.0 else 0.0 end)').alias('radiant_win_rate'), 
                    F.countDistinct('game_mode').alias('game_modes')
                ).withColumn('mart_loaded_at', F.current_timestamp())
        )
        daily.writeTo('lakehouse.mart.practice_match_daily').using('iceberg').createOrReplace()
        publish_table('mart', 'practice_match_daily', daily, description='Ежедневная витрина матчей с длительностью и долей побед Radiant', dependencies=['stage/practice_matches'])
        column_comments = {
            'match_date': 'Дата начала матчей',
            'matches': 'Количество матчей за дату',
            'avg_duration_seconds': 'Средняя длительность матча в секундах',
            'radiant_win_rate': 'Доля матчей с победой Radiant',
            'game_modes': 'Количество представленных режимов игры',
            'mart_loaded_at': 'Время расчёта витрины',
        }
        for column, comment in column_comments.items():
            spark.sql(f"alter table lakehouse.mart.practice_match_daily alter column `{column}` comment '{comment}'")
    daily.orderBy('match_date').show(100, False)


## code
with SparkSessionContext('jh-mart-events') as ctx:
    spark = ctx
    with ctx.lineage(
        'build-mart-kill-summary',
        inputs=['stage.practice_kill_events'],
        output='mart.practice_kill_summary',
        description='Сводка событий убийств по дате и атакующему',
        dataset_descriptions={
            'stage.practice_kill_events': 'События убийств с рассчитанным временем события',
            'mart.practice_kill_summary': 'Одна строка на сочетание даты события и атакующего',
        },
        columns={
            'event_date': 'stage.practice_kill_events.event_at',
            'attacker': 'stage.practice_kill_events.attacker',
            'kills': 'stage.practice_kill_events.id',
            'matches_with_kills': 'stage.practice_kill_events.match_id',
            'first_event_at': 'stage.practice_kill_events.event_at',
            'last_event_at': 'stage.practice_kill_events.event_at',
        },
        config={
            'grain': 'one row per event_date and attacker',
            'group_by': ['to_date(event_at)', 'attacker'],
            'metrics': ['count(*)', 'countDistinct(match_id)', 'min(event_at)', 'max(event_at)'],
        }
    ):
        result = (
            spark.table('lakehouse.stage.practice_kill_events')
                .groupBy(F.to_date('event_at').alias('event_date'), 'attacker')
                .agg(
                    F.count('*').alias('kills'), 
                    F.countDistinct('match_id').alias('matches_with_kills'), 
                    F.min('event_at').alias('first_event_at'), 
                    F.max('event_at').alias('last_event_at')
                ).withColumn('mart_loaded_at', F.current_timestamp())
        )
        result.writeTo('lakehouse.mart.practice_kill_summary').using('iceberg').createOrReplace()
        publish_table('mart', 'practice_kill_summary', result, description='Сводка событий убийств по дате и атакующему', dependencies=['stage/practice_kill_events'])
        column_comments = {
            'event_date': 'Дата события убийства',
            'attacker': 'Идентификатор атакующего игрока',
            'kills': 'Количество событий убийства',
            'matches_with_kills': 'Количество матчей с событиями убийства',
            'first_event_at': 'Время первого события в группе',
            'last_event_at': 'Время последнего события в группе',
            'mart_loaded_at': 'Время расчёта витрины',
        }
        for column, comment in column_comments.items():
            spark.sql(f"alter table lakehouse.mart.practice_kill_summary alter column `{column}` comment '{comment}'")
    spark.table('lakehouse.mart.practice_kill_summary').orderBy(F.desc('kills')).show(30, False)


## code
with SparkSessionContext('jh-mart-contract') as ctx:
    spark = ctx.spark
    spark.sql('describe table lakehouse.mart.practice_match_daily').show(100, False)
    spark.sql('select * from lakehouse.mart.practice_match_daily where matches < 0 or radiant_win_rate not between 0 and 1').show()
    spark.sql('select match_date, matches, round(avg_duration_seconds, 1) avg_duration, round(radiant_win_rate * 100, 1) radiant_win_percent from lakehouse.mart.practice_match_daily order by match_date').show()
