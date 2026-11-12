# Учебные примеры ETL — общие практики

Учебные ноутбуки изучены по исходному коду, **не запускались**. Оставлены только общие примеры, применимые к выбранным SQL №13, ML №16, LLM №22. Примеры реализации невыбранных кейсов удалены из рабочего комплекта.

| Ноутбук | Использование |
|---|---|
| [practice_01_source_analytics.ipynb](../examples/practice_01_source_analytics.ipynb) | Разведка PostgreSQL/MongoDB через DuckDB, обзор схем и проверка соединений |
| [practice_02_raw_profiling.ipynb](../examples/practice_02_raw_profiling.ipynb) | Профилирование источников и Iceberg RAW, уникальность и сверки |
| [practice_03_stage.ipynb](../examples/practice_03_stage.ipynb) | Преобразования RAW → STAGE, типизация и нормализация |
| [practice_04_mart.ipynb](../examples/practice_04_mart.ipynb) | STAGE → MART, публикация витрин |
| [practice_05_quality_iceberg.ipynb](../examples/practice_05_quality_iceberg.ipynb) | Data Quality, Iceberg и проверки метаданных |
| [practice_06_analytics.ipynb](../examples/practice_06_analytics.ipynb) | Аналитика поверх витрин и интерпретация |
| [practice_pipeline_spark.ipynb](../examples/practice_pipeline_spark.ipynb) | Сквозной Spark RAW → STAGE → MART |

**Общая схема:** PostgreSQL/MongoDB → Spark/Airflow → Iceberg RAW → STAGE → MART → Trino/Superset.

**Оговорки:** примеры используют учебные объекты `practice_*` и могут содержать демонстрационные данные, не равные фактическим объёмам. В `practice_01_source_analytics.ipynb` есть учётные данные в открытом виде: не публиковать без очистки. Наличие готового рабочего ETL не подтверждено.
