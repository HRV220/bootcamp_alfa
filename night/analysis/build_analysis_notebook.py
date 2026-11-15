"""Build and execute notebook code cells with CPython exec, not a Jupyter kernel."""
from pathlib import Path
import contextlib
import datetime
import hashlib
import io
import json
import platform
import time
import traceback

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def md(text):
    return {'cell_type':'markdown','metadata':{},'source':text.splitlines(True)}

def code(text):
    return {'cell_type':'code','metadata':{},'source':text.strip().splitlines(True),
            'execution_count':None,'outputs':[]}

cells = [
md('''# Профиль CSV кейса ML №18

Воспроизводимое описательное исследование локального `task/case2/smurf_players.csv`.
Одна строка — наблюдение игрока в матче. Это не обучение модели и не оценка качества детектора смурфов.

**Исполнение:** клетки последовательно выполнены CPython через `exec` в общем пространстве имён,
stdout фактически захвачен в outputs. Ядро Jupyter не запускалось.
Среда и статусы исполнения находятся в `notebook_execution.json`.
'''),
md('''## 1. Источник, период и контроль неизменности

Путь разрешается относительно корня проекта. Можно выполнить notebook из корня, `night/` или
`night/analysis/`. Используется только стандартная библиотека Python. Никаких сетевых обращений,
кластерных запусков и изменений исходного CSV нет. SHA-256 фиксирует конкретную версию выборки.
'''),
code('''from pathlib import Path
from collections import Counter, defaultdict
import csv, hashlib, json, math, statistics

project_root = next((p for p in [Path.cwd(), *Path.cwd().parents]
                     if (p / 'task/case2/smurf_players.csv').is_file()), None)
assert project_root is not None, 'Run inside the project directory'
source = project_root / 'task/case2/smurf_players.csv'
source_before = hashlib.sha256(source.read_bytes()).hexdigest()
with source.open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.DictReader(stream)
    fieldnames = reader.fieldnames
    rows = list(reader)
assert rows and fieldnames
print('Источник:', source.relative_to(project_root))
print('SHA-256:', source_before)
print('Наблюдения:', len(rows), 'Столбцы:', len(fieldnames))
print('Безымянный первый столбец:', '' in fieldnames, '(индекс экспорта, не бизнес-ключ)')
'''),
md('''## 2. Контракт и профилирование качества

Проверяем обязательные поля, уникальность ключей игрока в матче, форматы bool и числовые диапазоны.
Пустое значение `rank` нельзя заменять нулём или объявлять низким рангом.
Наличие всех положительных меток не означает, что происхождение разметки проверено.
'''),
code('''required = ['match_id','player_slot','account_id','hero_id','kills','deaths','assists',
            'kda','gold_per_min','xp_per_min','hero_damage','last_hits','dur_min','win','smurf']
assert set(required) <= set(fieldnames)
assert all(r[k] != '' for r in rows for k in required)
assert all(r['win'] in {'True','False'} for r in rows)
assert all(r['is_radiant'] in {'True','False'} for r in rows)
assert all(float(r['dur_min']) > 0 for r in rows)
assert all(float(r[k]) >= 0 for r in rows for k in
           ['kills','deaths','assists','gold_per_min','xp_per_min','hero_damage','last_hits'])
duplicates_slot = len(rows) - len({(r['match_id'],r['player_slot']) for r in rows})
duplicates_account = len(rows) - len({(r['match_id'],r['account_id']) for r in rows})
assert duplicates_slot == 0 and duplicates_account == 0
missing_counts = {k:sum(r[k] == '' for r in rows) for k in fieldnames}
entirely_missing = [k for k,n in missing_counts.items() if n == len(rows)]
labels = Counter(r['smurf'] for r in rows)
print('Дубли (match_id, player_slot):', duplicates_slot)
print('Дубли (match_id, account_id):', duplicates_account)
print('Полностью пустые поля:', ', '.join(entirely_missing))
print('Метки smurf:', dict(labels))
print('PASS: контракт обязательных полей и уникальности')
'''),
md('''## 3. Проверка производных признаков

Сверяем `kda = (kills + assists) / max(deaths, 1)`, `hd_pm = hero_damage / dur_min`
и `lh_pm = last_hits / dur_min`. Допуск абсолютного отклонения: 1e-6.
Проверка подтверждает арифметику файла, но не полноту и достоверность внешнего источника.
'''),
code('''formula_errors = []
for index, r in enumerate(rows, start=2):
    expected = {
        'kda': (float(r['kills']) + float(r['assists'])) / max(float(r['deaths']),1),
        'hd_pm': float(r['hero_damage']) / float(r['dur_min']),
        'lh_pm': float(r['last_hits']) / float(r['dur_min']),
    }
    for name, calculated in expected.items():
        if not math.isfinite(float(r[name])) or abs(float(r[name])-calculated) > 1e-6:
            formula_errors.append({'csv_line':index,'field':name,'expected':calculated,'actual':r[name]})
assert not formula_errors, formula_errors
print('Проверенных формул:', len(rows)*3)
print('Отклонений:', len(formula_errors))
print('PASS: KDA, урон/мин и last hits/мин')
'''),
md('''## 4. Описательные показатели выборки

Винрейт рассчитывается как доля побед среди строк этого файла. Это не глобальный винрейт аккаунта
и не причинный эффект. Повторные наблюдения одного аккаунта не являются независимыми игроками.
Пороговые количества ниже служат только описанием и не применяются как классификатор.
'''),
code('''accounts = sorted({r['account_id'] for r in rows})
matches = {r['match_id'] for r in rows}
wins = sum(r['win'] == 'True' for r in rows)
overall = {'observations':len(rows),'matches':len(matches),'accounts':len(accounts),
           'wins':wins,'win_rate_pct':100*wins/len(rows),
           'median_gpm':statistics.median(float(r['gold_per_min']) for r in rows),
           'median_xpm':statistics.median(float(r['xp_per_min']) for r in rows),
           'median_kda':statistics.median(float(r['kda']) for r in rows)}
print(json.dumps(overall, ensure_ascii=False, indent=2))
thresholds = {
    'KDA > 5':sum(float(r['kda']) > 5 for r in rows),
    'GPM > 700':sum(float(r['gold_per_min']) > 700 for r in rows),
    'Оба условия':sum(float(r['kda']) > 5 and float(r['gold_per_min']) > 700 for r in rows),
}
print('Описательные пороги:', json.dumps(thresholds, ensure_ascii=False))
'''),
md('''## 5. Таблица шести аккаунтов

Для каждого аккаунта показываем число наблюдавшихся матчей, победы, винрейт в выбранном файле
и медианы GPM, XPM и KDA. Медианы аккаунтов и медианы всех строк имеют разные веса.
'''),
code('''by_account = defaultdict(list)
for r in rows:
    by_account[r['account_id']].append(r)
account_table = []
for account, group in sorted(by_account.items()):
    account_wins = sum(r['win'] == 'True' for r in group)
    account_table.append({'account_id':account,'observations':len(group),
                          'matches':len({r['match_id'] for r in group}),
                          'wins':account_wins,'win_rate_pct':100*account_wins/len(group),
                          'median_gpm':statistics.median(float(r['gold_per_min']) for r in group),
                          'median_xpm':statistics.median(float(r['xp_per_min']) for r in group),
                          'median_kda':statistics.median(float(r['kda']) for r in group)})
assert len(account_table) == 6, 'Expected six accounts in this supplied file'
assert sum(r['observations'] for r in account_table) == len(rows)
assert sum(r['wins'] for r in account_table) == wins
print('| account_id | матчи | победы | винрейт, % | GPM медиана | XPM медиана | KDA медиана |')
print('|---|---:|---:|---:|---:|---:|---:|')
for r in account_table:
    print('| {} | {} | {} | {:.2f} | {:.1f} | {:.1f} | {:.3f} |'.format(
        r['account_id'],r['matches'],r['wins'],r['win_rate_pct'],
        r['median_gpm'],r['median_xpm'],r['median_kda']))
'''),
md('''## 6. Независимая сверка с существующим профилем

Перерасчёт выполнен непосредственно из CSV. Следующая клетка только читает артефакты
`profile_smurf.py` и сверяет с ними результаты. Их наличие не требуется для первых пяти разделов.
При наличии расхождений утверждения остановят исполнение.
'''),
code('''profile_path = project_root / 'night/analysis/smurf_profile.json'
assert profile_path.is_file(), 'Reproduce profile first: python night/analysis/profile_smurf.py'
profile = json.loads(profile_path.read_text(encoding='utf-8'))
assert profile['source_sha256'] == source_before
for key in ['observations','matches','accounts','wins','win_rate_pct']:
    assert math.isclose(profile['overall'][key], overall[key], abs_tol=1e-10)
assert profile['missing_counts'] == missing_counts
assert profile['label_counts'] == dict(labels)
assert profile['duplicate_player_match_keys'] == duplicates_slot
assert profile['duplicate_account_match_keys'] == duplicates_account
assert profile['derived_formula_errors'] == formula_errors
for r in account_table:
    existing = profile['per_account'][r['account_id']]
    assert r['observations'] == existing['observations']
    assert r['wins'] == existing['wins']
    for ours, theirs in [('median_gpm','gold_per_min'),('median_xpm','xp_per_min'),('median_kda','kda')]:
        assert math.isclose(r[ours], existing[theirs]['median'],abs_tol=1e-10)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_before
print('PASS: перерасчёт совпадает с smurf_profile.json')
print('PASS: исходный CSV не изменён')
'''),
md('''## 7. Выводы, ограничения и следующая проверка

В файле 87 наблюдений шести аккаунтов, 77 побед (88,51%). Медиана GPM равна 711.
Эти числа описывают выбранный файл и не оценивают распространённость смурфов.

- Все строки имеют `smurf=1`. Источник разметки не документирован, отрицательного класса и peer-контроля нет.
- `rank`, `calibration`, `rank_known`, `tier`, `kda_c`, `farm_pos`, `perf_z` полностью пусты.
- Нет временных меток матчей, режима и объективной позиции игрока, поэтому период и сопоставимость peers не подтверждены.
- Число матчей аккаунта в файле не равно размеру всей игровой истории и не доказывает «мало игр».
- Строки повторяются по аккаунтам, поэтому 87 строк нельзя считать 87 независимыми игроками.
- Isolation Forest не обучался. Accuracy, precision, recall, ROC-AUC и доля реальных смурфов не рассчитывались.

Для проверки ML-гипотезы нужен независимый набор обычных игроков и кандидатов, документированная
разметка, достаточная история на аккаунт, контекст роли и уровня матча, разбиение по аккаунтам и времени.
Порог аномальности следует выбирать на независимой валидации. Даже аномальный профиль сам по себе
не доказывает нарушение правил.
'''),
]

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
namespace = {'__name__':'__main__'}
records=[]
status='passed'
for cell_index, cell in enumerate(cells):
    cell['id'] = f'analysis-{cell_index:02d}'
    if cell['cell_type'] != 'code':
        continue
    count=len(records)+1
    cell['execution_count']=count
    src=''.join(cell['source'])
    buf=io.StringIO()
    clock=time.perf_counter()
    error=None
    try:
        with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
            exec(compile(src, f'analysis_review.ipynb#cell-{cell_index}', 'exec'),namespace)
    except Exception as exc:
        error={'ename':type(exc).__name__,'evalue':str(exc),'traceback':traceback.format_exc().splitlines()}
        status='failed'
    if buf.getvalue():
        cell['outputs'].append({'output_type':'stream','name':'stdout','text':buf.getvalue().splitlines(True)})
    if error:
        cell['outputs'].append({'output_type':'error',**error})
    records.append({'cell_index':cell_index,'execution_count':count,'status':'failed' if error else 'passed',
                    'duration_seconds':round(time.perf_counter()-clock,6),
                    'source_sha256':hashlib.sha256(src.encode()).hexdigest(),
                    'stdout':buf.getvalue(),'error':error})
    if error:
        break

nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
    'language_info':{'name':'python','version':platform.python_version()},
    'execution_method':'Sequential CPython exec with captured stdout; no Jupyter kernel was launched.'},
    'nbformat':4,'nbformat_minor':5}
target=OUT/'analysis_review.ipynb'
target.write_text(json.dumps(nb,ensure_ascii=False,indent=2),encoding='utf-8')
report={'started_at_utc':started,'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'method':'Sequential CPython exec in shared namespace; no Jupyter kernel launched',
        'python_version':platform.python_version(),'implementation':platform.python_implementation(),
        'status':status,'exit_code':0 if status=='passed' else 1,'code_cells_executed':len(records),
        'notebook_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'source_csv_sha256':namespace.get('source_before'),'cells':records}
(OUT/'notebook_execution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','exit_code','code_cells_executed','source_csv_sha256']},ensure_ascii=False))
raise SystemExit(report['exit_code'])
