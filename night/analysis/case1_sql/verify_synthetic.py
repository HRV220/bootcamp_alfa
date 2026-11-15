"""Execute the proposed SELECTs against SQLite synthetic edge fixtures.
Only qualified table names are mapped locally. This is not a Spark/Trino test.
Run: python night/analysis/case1_sql/verify_synthetic.py
"""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
conn.executescript('''
CREATE TABLE raw_matches(match_id INTEGER, start_time INTEGER, duration INTEGER,
 game_mode INTEGER, lobby_type INTEGER, radiant_win BOOLEAN);
CREATE TABLE raw_players(match_id INTEGER, player_slot INTEGER, account_id INTEGER,
 hero_id INTEGER, rank INTEGER, is_radiant BOOLEAN, win BOOLEAN);
CREATE TABLE raw_events(id TEXT, match_id INTEGER, steam_account_id INTEGER, itemid INTEGER, time INTEGER);
''')

def fixture(match, times=(200,), account=None, start=1791936000, duration=1800,
            game_mode=1, lobby=7, winner=True, win=None, rank=None):
    account = account if account is not None else match * 11
    conn.execute('INSERT INTO raw_matches VALUES(?,?,?,?,?,?)', (match,start,duration,game_mode,lobby,winner))
    conn.execute('INSERT INTO raw_players VALUES(?,?,?,?,?,?,?)',
                 (match,0,account,1,rank,True,winner if win is None else win))
    for i,t in enumerate(times):
        conn.execute('INSERT INTO raw_events VALUES(?,?,?,?,?)', (f'{match}_{i}',match,account,164,t))
    return account

fixture(1, (100,500)); fixture(2,(300,),winner=False)
fixture(3,(None,400)); fixture(4,(-1,400)); fixture(5,(100,1801))
fixture(6,(100,200,300)); fixture(7,(150,),account=4294967295)
fixture(8,(200,),account=4294967295)
conn.execute('INSERT INTO raw_players VALUES(8,1,4294967295,2,NULL,TRUE,TRUE)')
fixture(9); conn.execute('INSERT INTO raw_matches SELECT * FROM raw_matches WHERE match_id=9')
fixture(10); conn.execute('INSERT INTO raw_players VALUES(10,0,999,2,NULL,TRUE,TRUE)')
fixture(11,(100,200)); conn.execute("UPDATE raw_events SET id='duplicate' WHERE match_id=11")
fixture(12); conn.execute("INSERT INTO raw_events VALUES('12_0',12,132,999,100)")
fixture(13,start=1791935999); fixture(14,(250,),start=1791936000)
fixture(15,start=1792108800); fixture(16,account=0); fixture(17,win=False)
fixture(18,game_mode=None); fixture(19)
conn.execute('UPDATE raw_events SET id=NULL WHERE match_id=19')
fixture(20); conn.execute('DELETE FROM raw_matches WHERE match_id=20')
fixture(21); conn.execute('DELETE FROM raw_players WHERE match_id=21')
fixture(22,duration=0)
fixture(23,(100,),account=2301)
conn.execute('INSERT INTO raw_players VALUES(23,128,2302,2,20,FALSE,FALSE)')
conn.execute("INSERT INTO raw_events VALUES('23_second',23,2302,164,300)")
fixture(24,game_mode=15); fixture(25,lobby=1); fixture(26)
conn.execute('UPDATE raw_players SET hero_id=NULL WHERE match_id=26')
fixture(27); conn.execute('UPDATE raw_players SET is_radiant=NULL WHERE match_id=27')
fixture(28,winner=None); fixture(29,account=-1); fixture(30,lobby=None)
fixture(31,start=None); fixture(32)
conn.execute('UPDATE raw_events SET steam_account_id=NULL WHERE match_id=32')
conn.execute("INSERT INTO raw_events VALUES('null_match',NULL,1,164,100)")

table_map = {
    'lakehouse.raw.pg__matches': 'raw_matches',
    'lakehouse.raw.pg__match_players': 'raw_players',
    'lakehouse.raw.mongo__purchase_events': 'raw_events',
    'lakehouse.stage.night_case1_purchase_events': 'stage_events',
    'lakehouse.mart.night_case1_first_purchase': 'mart_first',
    'lakehouse.mart.night_case1_winrate': 'mart_summary',
}
def sql(name):
    text = (BASE/name).read_text(encoding='utf-8')
    for source,target in table_map.items():
        text = text.replace(source,target)
    return text

def build(name,query):
    conn.execute(f'DROP TABLE IF EXISTS {name}')
    conn.execute(f'CREATE TABLE {name} AS ' + query)

checks=[]
def check(name,condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'check':name, 'status':'pass'})

build('stage_events',sql('01_purchase_events.sql'))
raw_count=conn.execute('SELECT COUNT(*) FROM raw_events WHERE itemid=164').fetchone()[0]
stage_count=conn.execute('SELECT COUNT(*) FROM stage_events').fetchone()[0]
check('Every raw item-164 row retained without join multiplication',raw_count==stage_count)
build('mart_first',sql('02_first_purchase.sql'))
first=[dict(r) for r in conn.execute('SELECT * FROM mart_first')]
expected={(1,11),(2,22),(7,4294967295),(14,154),(23,2301),(23,2302)}
actual={(r['match_id'],r['steam_account_id']) for r in first}
check('Exactly the six expected valid buyer-match pairs survive',actual==expected)
check('Null, negative, after-end and >2 event pairs excluded in full',not ({3,4,5,6}&{r['match_id'] for r in first}))
check('Anonymous buyer retained only when unambiguous', any(r['match_id']==7 for r in first) and not any(r['match_id']==8 for r in first))
check('Conflicting match, slot, event ID and cross-item event ID quarantined', not ({9,10,11,12}&{r['match_id'] for r in first}))
check('Period is UTC start-inclusive and end-exclusive', (14,154) in actual and not ({13,15}&{r['match_id'] for r in first}))
check('Missing keys/context, bot, inconsistent outcome and null mode excluded',not ({16,17,18,19,20,21,22}&{r['match_id'] for r in first}))
check('Unknown rank retained', any(r['match_id']==1 and r['rank_is_unknown']==1 for r in first))
check('First event chosen after full-pair validation', next(r for r in first if r['match_id']==1)['first_purchase_time_sec']==100)
check('Even exact median equals 200 seconds',all(r['median_purchase_time_sec']==200 for r in first))
check('Both sides and both timing groups can remain in one match',len([r for r in first if r['match_id']==23])==2)
check('History remains unknown and provisional',all(r['history_complete'] is None and r['is_provisional']==1 for r in first))
build('mart_summary',sql('03_winrate.sql'))
summary=dict(conn.execute('SELECT * FROM mart_summary').fetchone())
check('Win rates use buyer denominators and percentage-point subtraction',
      summary['early_n']==3 and summary['late_n']==3 and summary['early_wins']==3
      and summary['late_wins']==1 and abs(summary['win_rate_diff_pp']-200/3)<1e-9)
quality=dict(conn.execute(sql('04_quality_checks.sql')).fetchone())
check('Quality report covers all retained events',quality['source_dominator_events']==raw_count)
pair_diagnostics=[dict(r) for r in conn.execute(sql('05_pair_diagnostics.sql'))]
check('Excessive purchase count remains available in diagnostics',next(r for r in pair_diagnostics if r['match_id']==6)['exceeds_purchase_limit']==1)

# A malformed/mixed stage generation must not publish a pair.
conn.execute("UPDATE stage_events SET stage_loaded_at='different' WHERE event_id='1_1'")
build('mart_first',sql('02_first_purchase.sql'))
check('Mixed stage generation within a pair excluded',conn.execute('SELECT COUNT(*) FROM mart_first WHERE match_id=1').fetchone()[0]==0)
check('Mixed stage generation blocks the entire publication',conn.execute('SELECT COUNT(*) FROM mart_first').fetchone()[0]==0)

# A tied odd median puts all ties into early, even when groups are unequal.
conn.execute('DELETE FROM stage_events')
for match,time in [(1,100),(2,150),(7,150)]:
    conn.execute('INSERT INTO stage_events SELECT * FROM ('+sql('01_purchase_events.sql')+') WHERE match_id=?',(match,))
    conn.execute('UPDATE stage_events SET purchase_time_sec=? WHERE match_id=?',(time,match))
build('mart_first',sql('02_first_purchase.sql'))
tied=[dict(r) for r in conn.execute('SELECT * FROM mart_first')]
# Match1 contains two events and is still exactly one buyer.
check('Odd median and boundary ties are exact',len(tied)==3 and all(r['median_purchase_time_sec']==150 and r['timing_group']=='early' for r in tied))
build('mart_summary',sql('03_winrate.sql'))
one_group=dict(conn.execute('SELECT * FROM mart_summary').fetchone())
check('Missing late group yields NULL rate, effect and target',one_group['late_n']==0 and one_group['late_win_rate_pct'] is None and one_group['win_rate_diff_pp'] is None and one_group['target_reached'] is None)
conn.execute('DELETE FROM stage_events')
build('mart_first',sql('02_first_purchase.sql')); build('mart_summary',sql('03_winrate.sql'))
empty=dict(conn.execute('SELECT * FROM mart_summary').fetchone())
check('Empty input yields zero counts and NULL median/effect',empty['buyers_count']==0 and empty['median_purchase_time_sec'] is None and empty['win_rate_diff_pp'] is None)
report={'scope':'Actual SQL SELECT logic on synthetic SQLite fixtures, table names mapped locally',
        'cluster_execution':False,'spark_trino_compatibility_verified':False,
        'synthetic_raw_dominator_events':raw_count,'checks':checks,'passed':len(checks),
        'failed':0,'fixture_summary_do_not_use_as_real_result':summary}
(BASE/'synthetic_check_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'failed':0,'cluster_execution':False},ensure_ascii=False))
