# practice_05_quality_iceberg.ipynb

## markdown
# 5. Качество данных, Iceberg и занимаемое место
Проверим контракт данных, историю версий Iceberg, списки манифестов, размеры файлов, потерянные файлы и изменение схемы. В конце оформим отчёт о качестве для владельца таблицы.

## markdown
## Как проверять качество и устройство таблицы

Проверка качества — это не только поиск пустой таблицы. Для каждой витрины нужно заранее определить проверяемые свойства и ожидаемое поведение:

- таблица не должна быть пустой;
- обязательные поля не должны содержать `null`;
- ключи должны быть уникальными, если это предусмотрено моделью;
- числовые показатели должны находиться в допустимом диапазоне;
- дата загрузки должна показывать ожидаемую свежесть;
- количество строк должно быть согласовано с предыдущим слоем и источником.

Iceberg хранит не только данные, но и историю их состояний. Поэтому здесь отдельно рассматриваются:

- **версия таблицы** — состояние таблицы после отдельной фиксации изменений;
- **манифест** — служебный список файлов, входящих в состояние таблицы;
- **файл данных** — физический файл с записями;
- **изменение схемы** — добавление или изменение полей по правилам Iceberg;
- **согласованность хранения** — отсутствие файлов, на которые таблица больше не ссылается.

Не запускайте операции обслуживания только ради уменьшения числа файлов. Перед изменением нужно зафиксировать текущую версию таблицы, количество записей, число файлов и занимаемый объём. Операции удаления старых версий и потерянных файлов могут сделать недоступным восстановление к прежнему состоянию.

Результат проверки оформляется как отчёт: название проверки, фактическое значение, ожидаемое значение, статус, серьёзность нарушения, ответственный и рекомендуемое действие.

## code
from lakehouse_spark import SparkSessionContext
with SparkSessionContext('jh-quality-contracts') as ctx:
    spark = ctx
    table = 'lakehouse.mart.practice_match_daily'
    with ctx.lineage(
        'check-mart-match-daily-quality',
        inputs=['mart.practice_match_daily'],
        description='Проверка контракта ежедневной витрины матчей',
        dataset_descriptions={
            'mart.practice_match_daily': 'Витрина с одной строкой на дату матча',
        },
        config={
            'checks': ['not_empty', 'non_negative_matches', 'rate_range', 'unique_date'],
            'result': 'PASS или FAIL для каждой проверки',
        }
    ):
        checks = {
          'not_empty': f'select count(*) > 0 passed from {table}',
          'non_negative_matches': f'select count_if(matches < 0) = 0 passed from {table}',
          'rate_range': f'select count_if(radiant_win_rate < 0 or radiant_win_rate > 1) = 0 passed from {table}',
          'unique_date': f'select count(*) = count(distinct match_date) passed from {table}',
        }
        for name, sql in checks.items():
            passed = spark.sql(sql).first().passed
            print(name, 'PASS' if passed else 'FAIL')


## code
with SparkSessionContext('jh-iceberg-metadata') as ctx:
    spark = ctx
    table = 'lakehouse.mart.practice_match_daily'
    with ctx.lineage(
        'inspect-mart-match-daily-metadata',
        inputs=['mart.practice_match_daily'],
        description='Просмотр истории версий, файлов и манифестов витрины',
        config={
            'metadata': ['history', 'files', 'manifests'],
            'purpose': 'оценка изменений и занимаемого места',
        }
    ):
        print('История версий')
        spark.sql(f'select * from {table}.history order by made_current_at desc').show(20, False)
        print('Файлы')
        spark.sql(f'select content, file_format, record_count, file_size_in_bytes, file_path from {table}.files').show(100, False)
        print('Манифесты')
        spark.sql(f'select * from {table}.manifests').show(20, False)


## code
with SparkSessionContext('jh-iceberg-maintenance') as ctx:
    spark = ctx
    table = 'lakehouse.mart.practice_match_daily'
    with ctx.lineage(
        'inspect-mart-maintenance',
        inputs=['mart.practice_match_daily'],
        description='Оценка размера витрины и подготовка безопасных операций обслуживания',
        config={
            'measurements': ['files', 'records', 'bytes'],
            'operations_only_after_review': ['rewrite_data_files', 'expire_snapshots'],
            'retention_required': True,
        }
    ):
        files = spark.sql(f'select sum(file_size_in_bytes) bytes, sum(record_count) records, count(*) files from {table}.files').first()
        print({'files': files.files, 'records': files.records, 'bytes': files.bytes, 'MiB': round((files.bytes or 0) / 1024 / 1024, 3)})
        print('Запускайте обслуживание только после проверки политики хранения версий:')
        print('call lakehouse.system.rewrite_data_files(table =>', table, ')')
        print('call lakehouse.system.expire_snapshots(table =>', table, ', older_than => timestamp 2026-01-01 00:00:00)')
