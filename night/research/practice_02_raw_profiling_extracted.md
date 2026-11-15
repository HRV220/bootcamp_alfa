# practice_02_raw_profiling.ipynb

## markdown
### Аналитика сырого слоя
Сырой слой сохраняет данные источника и технические поля загрузки.
</br>Для начала проверим имеющиеся объекты и их артефакты.

## markdown
### Термины профилирования RAW

- **профилирование** — расчёт числа строк, уникальных значений, пропусков, диапазонов и распределений;
- **технические поля** — время и идентификатор загрузки, которые помогают проверить происхождение и актуальность записи;
- **сверка** — сопоставление объектов разных источников по общему ключу;
- **ожидаемое состояние источника** — контрольные значения, с которыми сравнивается фактическое состояние RAW;
- **контракт данных** — формализованные требования к структуре и содержимому таблицы.

Spark выполняет преобразования лениво: `table`, `select`, `where` и `groupBy` только строят план. Чтение запускается действиями `show`, `count`, `first` или `collect`. Поэтому ошибки доступа к Iceberg или объектному хранилищу обычно проявляются на действии.

## markdown
### Как работает SparkSessionContext

`SparkSessionContext` создаёт короткоживущую Spark-сессию для одного логического блока notebook и гарантированно вызывает `spark.stop()` при выходе из `with`, в том числе при ошибке. Это освобождает driver и ресурсы Spark-кластера и не оставляет неактивные приложения после выполнения ячейки. Один экземпляр context manager нельзя использовать повторно.

Базовое использование:

```python
with SparkSessionContext('jh-raw-profiles') as ctx:
    spark = ctx
    spark.table('lakehouse.raw.pg__matches').show()
```

`ctx` делегирует методы настоящей Spark-сессии, поэтому через него доступны `table`, `sql`, `read`, `conf` и другие Spark API. Сама сессия также доступна явно как `ctx.spark`. Явная форма полезна, когда одновременно используется `ctx.lineage(...)`:

```python
with SparkSessionContext('jh-example') as ctx:
    spark = ctx.spark
    with ctx.lineage('example-job', inputs=['raw.source'], output='stage.result'):
        spark.sql('select 1').show()
```

Конструктор принимает параметры:

- `app_name` — обязательное имя Spark application, отображаемое в Spark UI; используйте понятное уникальное имя задачи;
- `log_level='WARN'` — уровень логов Spark, например `ERROR`, `WARN`, `INFO` или `DEBUG`;
- `config=None` — словарь дополнительных Spark-настроек, применяемых до создания сессии;
- `lineage_namespace='jh'` — резервный namespace для нестандартных имён; стандартные `raw.*`, `stage.*` и `mart.*` автоматически маршрутизируются в `lakehouse_raw`, `jh_stage` и `jh_mart`.

Пример с параметрами:

```python
with SparkSessionContext(
    'jh-custom-query',
    log_level='ERROR',
    config={'spark.sql.shuffle.partitions': '8'},
    lineage_namespace='jh',
) as ctx:
    ctx.sql('select current_catalog()').show()
```

Не создавайте глобальную Spark-сессию на всю тетрадку. Объединяйте связанные действия в один `with`, а независимые проверки выполняйте в отдельных контекстах.

## markdown
Просмотр частичного списка объектов сырого слоя:

## code
from lakehouse_spark import SparkSessionContext

with SparkSessionContext('jh-raw-inventory') as ctx:
    spark = ctx
    spark.sql('show tables in lakehouse.raw').show(10, False)

## markdown
Просмотр архитектуры конкретного объекта:

## code
with SparkSessionContext('jh-raw-inventory') as ctx:
    spark = ctx
    table = f'lakehouse.raw.pg__matches'
    spark.sql(f'describe table {table}').show(100, False)

## markdown
### Профилирование сырого слоя
Далее проверим поля объекта на соответствие необходимым условиям.

## markdown
### SQL и DataFrame API в Spark

Одну проверку можно выразить SQL-запросом или цепочкой DataFrame API. SQL удобен для чтения бизнес-правил, DataFrame API — для программной сборки запросов и повторного использования промежуточных таблиц. Оба варианта выполняются движком Spark.

```python
with SparkSessionContext('jh-raw-example') as ctx:
    spark = ctx

    # SQL
    spark.sql('''
        select game_mode, count(*) as rows
        from lakehouse.raw.pg__matches
        group by game_mode
        order by game_mode
    ''').show()

    # DataFrame API
    (
        spark.table('lakehouse.raw.pg__matches')
            .groupBy('game_mode')
            .count()
            .orderBy('game_mode')
            .show()
    )
```

Для изучения физического плана используйте `explain(mode='formatted')`. Так можно увидеть чтение файлов, фильтры, объединения и перераспределение данных между исполнителями.

## code
with SparkSessionContext('jh-raw-profiles') as ctx:
    spark = ctx

    matches = spark.table('lakehouse.raw.pg__matches')
    (
        matches.selectExpr(
            'count(*) rows',
            'count(distinct match_id) distinct_match_ids',
            'count_if(match_id is null) null_match_ids',
            'min(from_unixtime(start_time)) min_start_epoch',
            'max(from_unixtime(start_time)) max_start_epoch',
            'min(loaded_at) min_loaded',
            'max(loaded_at) max_loaded'
        ).show(truncate=False)
    )
    matches.groupBy('game_mode').count().orderBy('game_mode').show()

## code
with SparkSessionContext('jh-raw-reconciliation') as ctx:
    spark = ctx
    matches = spark.table('lakehouse.raw.pg__matches').select('match_id').distinct()
    events = spark.table('lakehouse.raw.mongo__kill_events').select('match_id').distinct()
    
    print('Events without a match:')
    events.join(matches, 'match_id', 'left_anti').show(10, False)
    print('Matches without events:')
    matches.join(events, 'match_id', 'left_anti').show(10, False)
    
    print('Duplicate event IDs:')
    spark.table('lakehouse.raw.mongo__kill_events').groupBy('id').count().filter('count > 1').show(10, False)


## markdown
#### Сверка с источником
Для проверки ожидаемого количества строк за какой-то временной промежуток необходимо спросить его у владельца системы-источника или попробовать самостоятельно его выяснить, подключившись к системе.

## code
source_manifest = {
    'pg__matches': {'rows': 130998}, 
    'mongo__kill_events': {'rows': 9962562}
}

with SparkSessionContext('jh-raw-manifest-check') as ctx:
    spark = ctx
    for name, expected in source_manifest.items():
        actual = spark.table(f'lakehouse.raw.{name}').count()
        print(
            name, 
            {
                'expected': expected['rows'], 'actual': actual, 'status': 'PASS' 
                if actual == expected['rows'] else 'INVESTIGATE'
            }
        )
