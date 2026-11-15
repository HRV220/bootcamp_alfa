# practice_06_analytics.ipynb

## markdown
# 6. Аналитический результат
Последняя практика превращает витрины в воспроизводимый аналитический вывод. Важно отделять факт, метрику, интерпретацию и ограничение покрытия данных.

В текущем хранилище игровые события покрывают ограниченный период, поэтому выводы нельзя автоматически переносить на весь сезон.

## markdown
## Как оформить аналитический вывод

Аналитический результат должен позволять другому человеку понять не только число, но и способ его получения. Перед интерпретацией результата зафиксируйте:

- **вопрос** — на что именно отвечает расчёт;
- **совокупность** — какие записи вошли в расчёт;
- **период** — даты начала и конца наблюдения;
- **источники** — таблицы и их версии;
- **уровень детализации** — что представляет одна строка результата;
- **фильтры** — какие записи исключены и почему;
- **определение метрики** — формулу, единицы измерения и способ округления;
- **результат** — само значение и подходящее сравнение;
- **неопределённость** — что может влиять на устойчивость вывода;
- **качество и актуальность** — какие проверки пройдены и насколько свежи данные;
- **ограничения** — какие вопросы нельзя надёжно решить по имеющемуся покрытию;
- **следующее действие** — какую проверку или загрузку нужно выполнить дальше.

OpenLineage помогает связать вывод с исходными таблицами и запуском расчёта. Для аналитического запроса укажите имя операции, входную витрину, описание вопроса и правила расчёта. Если результат только выводится на экран и не записывается в таблицу, можно оставить `output` пустым, но описание запуска всё равно должно объяснять, какой ответ получен.

В этой тетрадке отдельно проверяется покрытие дат. Наличие результата не означает, что данные описывают весь сезон: сначала сравните период наблюдения с периодом, о котором задан вопрос.

## code
from lakehouse_spark import SparkSessionContext
with SparkSessionContext('jh-analytics-result') as ctx:
    spark = ctx
    with ctx.lineage(
        'answer-match-duration-question',
        inputs=['mart.practice_match_daily'],
        description='Ответ на вопрос о распределении матчей, длительности и победах Radiant по датам',
        dataset_descriptions={
            'mart.practice_match_daily': 'Ежедневная витрина матчей',
        },
        config={
            'grain': 'one row per match_date',
            'metrics': ['matches', 'avg_duration_seconds', 'radiant_win_percent', 'game_modes'],
            'rounding': 'duration and win rate rounded for presentation',
        }
    ):
        answer = spark.sql('''
            select match_date, matches, round(avg_duration_seconds, 1) avg_duration_seconds, 
                round(radiant_win_rate * 100, 1) radiant_win_percent, game_modes 
            from lakehouse.mart.practice_match_daily order by match_date
        ''')
        answer.show(100, False)


## code
with SparkSessionContext('jh-analytics-segments') as ctx:
    spark = ctx
    with ctx.lineage(
        'build-match-duration-segments',
        inputs=['mart.practice_match_daily'],
        description='Группировка дней по средней длительности матчей и проверка покрытия данных',
        config={
            'segments': {'short': '< 1200 seconds', 'medium': '1200-2399 seconds', 'long': '>= 2400 seconds'},
            'coverage': ['first_date', 'last_date', 'matches'],
        }
    ):
        print('Сегменты длительности')
        spark.sql('''
            select 
                case 
                    when avg_duration_seconds < 1200 then 'short' 
                    when avg_duration_seconds < 2400 then 'medium' 
                    else 'long' 
                end duration_segment, 
                sum(matches) matches, round(sum(radiant_win_rate * matches) / sum(matches), 3) win_rate 
            from lakehouse.mart.practice_match_daily group by 1 order by 1''').show()
        
        print('Покрытие и актуальность')
        spark.sql('''
            select min(match_date) first_date, max(match_date) last_date, sum(matches) matches 
            from lakehouse.mart.practice_match_daily
        ''').show()
