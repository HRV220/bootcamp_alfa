# Кейс 2 — логическая ER-модель ML-процесса

Эта схема объединяет исходные данные, вычисляемые сущности и результаты модели. `ML_SAMPLES`, `PEER_REFERENCE`, `ML_PREDICTIONS` выделены из кода как логические сущности; SQL-таблиц с такими именами в материалах нет.

```mermaid
erDiagram
    MATCHES |o..o{ MATCH_PLAYERS : "match_id; contextual"
    HEROES |o..o{ MATCH_PLAYERS : "hero_id"
    MATCH_PLAYERS |o..o| SMURF_OBSERVATIONS : "match_id + player_slot; align snapshots"
    MATCH_PLAYERS ||..o| ML_SAMPLES : "match_id + player_slot; in memory"
    PEER_REFERENCE |o..o{ ML_SAMPLES : "tier + farm_pos; fitted on train"
    ML_SAMPLES ||..o| ML_PREDICTIONS : "selected model; test rows"

    MATCHES {
        bigint match_id PK
        int start_time
        int duration
        int game_mode
        int lobby_type
        boolean radiant_win
    }
    HEROES {
        int hero_id PK
        string localized_name
        string_array roles
    }
    MATCH_PLAYERS {
        bigint match_id PK,FK
        int player_slot PK
        bigint account_id
        int hero_id FK
        int rank
        int kills
        int deaths
        int assists
        float kda
        int gold_per_min
        int xp_per_min
        int hero_damage
        int last_hits
        boolean is_radiant
        boolean win
    }
    SMURF_OBSERVATIONS {
        bigint match_id PK,FK
        int player_slot PK,FK
        bigint account_id
        int hero_id
        int gold_per_min
        int xp_per_min
        float kda
        int hero_damage
        int last_hits
        boolean win
        int rank "all NULL"
        boolean calibration "all NULL; type pending"
        boolean rank_known "all NULL; type pending"
        boolean anon
        int tier "all NULL; type pending"
        double dur_min
        double hd_pm
        double lh_pm
        double kda_c "all NULL; type pending"
        int farm_pos "all NULL; type pending"
        double perf_z "all NULL; type pending"
        int smurf "all 1; label origin unknown"
    }
    ML_SAMPLES {
        bigint match_id PK,FK
        int player_slot PK,FK
        bigint account_id
        int hero_id
        string group
        boolean rank_known
        int calibration
        boolean anon
        double tier FK
        double farm_pos FK
        double dur_min
        double hd_pm
        double lh_pm
        double kda_c
        double perf_z
        int smurf
        boolean label_ok
    }
    PEER_REFERENCE {
        double tier PK
        double farm_pos PK
        json mu "means of five metrics"
        json sd "std of five metrics"
    }
    ML_PREDICTIONS {
        bigint match_id PK,FK
        int player_slot PK,FK
        int yte "heuristic target"
        double pte "CatBoost probability"
        double thr "selected on validation"
    }
```

## Основания и статус сущностей

| Сущность | Основание | Статус |
|---|---|---|
| `MATCH_PLAYERS` | `load_raw()` читает `SELECT * FROM dota.match_players` | Физическая таблица, основной вход ноутбука |
| `MATCHES`, `HEROES` | Описание источников проекта | Предметный контекст; текущий ноутбук их не читает |
| `SMURF_OBSERVATIONS` | `smurf_players.csv` | Фактический отдельный CSV кандидатов; не вход по умолчанию |
| `ML_SAMPLES` | Результат `engineer()`, затем `SmurfLabeler.transform()` | DataFrame в памяти |
| `PEER_REFERENCE` | `SmurfLabeler.mu_` и `sd_` по `tier × farm_pos` | Логическое объединение статистик, рассчитанных на train |
| `ML_PREDICTIONS` | Тестовые строки `test`, цели `yte`, вероятности `pte`, порог `thr` | Логическое объединение результатов одной выбранной модели |

## Ключи и связи

Участник определяется парой `(match_id, player_slot)`. `account_id` не является первичным ключом участника. В CSV эта пара уникальна на текущих 87 строках; соответствие с текущим снимком PostgreSQL не проверено. Поэтому связь CSV с участниками — предполагаемое сопоставление по ключу после сверки снимков, а не подтверждённый FK.

`ML_SAMPLES` наследует ключ участника, но ноутбук отдельно не проверяет его уникальность. Ключ `PEER_REFERENCE` — `(tier, farm_pos)` в пределах одного обученного разметчика. `mu` и `sd` компактно обозначают средние и стандартные отклонения пяти метрик: GPM, XPM, `hd_pm`, `lh_pm`, `kda_c`. В коде они хранятся в двух DataFrame, а не в JSON-столбцах.

Для `ML_PREDICTIONS` пара `(match_id, player_slot)` является ключом только в пределах одной конфигурации и тестовой выборки. В коде `pte` — массив, связанный с `test` по позиции. Версионирование моделей и отдельные таблицы прогнозов не реализованы.

`||` — ровно один, `|o`/`o|` — ноль или один, `o{` — ноль или много. Пунктир обозначает неидентифицирующую связь. `PK`/`FK` у вычисляемых сущностей — логические ключи, не ограничения СУБД. Для пустых столбцов CSV типы с пометкой `type pending` предположены по смыслу.

## Что рассчитывается

`dur_min = (gold + gold_spent) / gold_per_min` — оценка длительности, не фактическое время из `matches`. `farm_pos` — место по GPM в команде конкретного матча, не подтверждённая роль. `perf_z` — среднее доступных z-оценок относительно группы `tier × farm_pos`.

Метка `smurf` формируется эвристикой: известный ранг, `tier <= 5`, `perf_z >= 1.5`. CatBoost обучается воспроизводить эту метку; Optuna подбирает параметры, порог выбирается на validation, SHAP объясняет прогнозы. Такая метка не является независимым подтверждением смурфинга.

В текущем тексте `engineer()` есть `return df d` и обращение к неопределённому `f` при построении группы. Поэтому схема описывает структуру алгоритма, а сохранённые выводы ноутбука не подтверждают воспроизводимость текущего кода. Код при подготовке схем не изменялся и не запускался.

Источники: [ноутбук](smurf_pipeline_fixed_with_outputs_1__1.ipynb), [CSV](smurf_players.csv), [описание источников](../../requirements/Источники.%20Описание%20полей%20таблиц.md).

[Mermaid-исходник](er_logical.mmd) · [Фактическая модель](er_physical.md)
