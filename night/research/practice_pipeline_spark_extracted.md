# practice_pipeline_spark.ipynb

## markdown
# Практика: полный Spark pipeline

Сквозной учебный pipeline: RAW → чтение и профиль → STAGE → сверка с RAW → MART → независимые проверки. Все Spark-приложения запускаются через `SparkSessionContext`.

## markdown
## Цель и grain

Источник `lakehouse.raw.pg__matches` содержит матчи. STAGE сохраняет одну строку на валидный матч, MART содержит одну строку на дату и игровой режим. Перед записью проверяем количество строк, уникальность ключа и отсутствие обязательных NULL.

## code
from lakehouse_spark import SparkSessionContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

CONFIG = {
    'spark.sql.adaptive.enabled': 'true',
    'spark.sql.shuffle.partitions': '8',
    'spark.sql.session.timeZone': 'UTC',
}

with SparkSessionContext('pipeline-practice-raw-stage-mart', config=CONFIG) as ctx:
    spark = ctx.spark
    raw = spark.table('lakehouse.raw.pg__matches')
    raw.printSchema()
    raw.show(10, truncate=False)
    raw_count = raw.count()
    print('RAW rows:', raw_count)

    # STAGE: выбор колонок, типизация, очистка и контролируемая дедупликация.
    stage = (raw.select('match_id', 'start_time', 'duration', 'game_mode', 'human_players', 'radiant_win')
        .withColumn('match_id', F.col('match_id').cast('long'))
        .withColumn('start_time', F.to_timestamp(F.from_unixtime(F.col('start_time').cast('long'))))
        .withColumn('duration_seconds', F.col('duration').cast('int'))
        .withColumn('game_mode', F.col('game_mode').cast('int'))
        .withColumn('human_players', F.col('human_players').cast('int'))
        .withColumn('radiant_win', F.col('radiant_win').cast('boolean'))
        .filter(F.col('match_id').isNotNull() & (F.col('duration_seconds') > 0))
        .withColumn('match_date', F.to_date('start_time'))
        .withColumn('duration_minutes', F.round(F.col('duration_seconds') / F.lit(60.0), 1)))
    latest = Window.partitionBy('match_id').orderBy(F.col('start_time').desc_nulls_last())
    stage = stage.withColumn('_row_number', F.row_number().over(latest)).filter(F.col('_row_number') == 1).drop('_row_number')
    stage.createOrReplaceTempView('stage_matches')
    stage.show(10, truncate=False)

    # Сверка RAW и STAGE: отбрасывание должно быть объяснимым.
    valid_raw = raw.filter(F.col('match_id').isNotNull() & (F.col('duration').cast('int') > 0)).select('match_id').distinct()
    stage_keys = stage.select('match_id').distinct()
    missing_after_stage = valid_raw.join(stage_keys, 'match_id', 'left_anti').count()
    duplicate_stage_keys = stage.count() - stage.select('match_id').distinct().count()
    print('RAW:', raw_count, 'valid RAW keys:', valid_raw.count(), 'STAGE:', stage.count())
    assert missing_after_stage == 0, f'Missing valid RAW keys: {missing_after_stage}'
    assert duplicate_stage_keys == 0, f'Duplicate STAGE keys: {duplicate_stage_keys}'

    # MART через DataFrame API.
    mart = (stage.groupBy('match_date', 'game_mode')
        .agg(F.count('*').alias('matches_count'), F.avg('duration_minutes').alias('avg_duration_minutes'),
             F.sum(F.when(F.col('radiant_win'), 1).otherwise(0)).alias('radiant_wins'))
        .withColumn('radiant_win_rate', F.col('radiant_wins') / F.col('matches_count')))
    mart.createOrReplaceTempView('mart_match_daily')
    mart.printSchema()
    mart.show(truncate=False)

    # Независимая SQL-сверка MART и проверка grain.
    mart_sql = spark.sql('''SELECT match_date, game_mode, COUNT(*) AS matches_count
        FROM stage_matches GROUP BY match_date, game_mode''')
    assert mart.select('match_date', 'game_mode').count() == mart.select('match_date', 'game_mode').distinct().count()
    assert mart.filter(F.col('matches_count') <= 0).count() == 0
    assert mart_sql.count() == mart.count()

    # В production после успешных проверок: 
    # stage.writeTo('lakehouse.stage.practice_matches').using('iceberg').createOrReplace()
    # mart.writeTo('lakehouse.mart.practice_match_daily').using('iceberg').createOrReplace()
    print('Pipeline checks passed')


## markdown
## Что проверить самостоятельно

1. Сравните `COUNT(*)` и `COUNT(DISTINCT match_id)` в RAW.
2. Найдите строки, отброшенные фильтром STAGE, и объясните причину.
3. Перепишите MART через Spark SQL.
4. Добавьте join со справочником героев или режимов и проверьте, не размножились ли строки.
5. Сравните результат до и после записи повторным чтением таблицы.