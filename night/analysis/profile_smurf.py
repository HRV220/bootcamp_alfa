"""Reproduce descriptive CSV audit. No model or smurf truth labels inferred.
Run from project root: python night/analysis/profile_smurf.py
Outputs stay inside night/analysis. Uses Python standard library only.
"""
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'task/case2/smurf_players.csv'
OUT = Path(__file__).resolve().parent
rows = list(csv.DictReader(SOURCE.open(encoding='utf-8-sig', newline='')))
fields = list(rows[0])
numeric = ['kills', 'deaths', 'assists', 'kda', 'gold_per_min', 'xp_per_min',
           'net_worth', 'hero_damage', 'tower_damage', 'dur_min', 'hd_pm', 'lh_pm']

def summary(rs):
    result = {'observations': len(rs), 'matches': len({r['match_id'] for r in rs}),
              'accounts': len({r['account_id'] for r in rs}),
              'wins': sum(r['win'] == 'True' for r in rs)}
    result['win_rate_pct'] = result['wins'] / len(rs) * 100
    for k in numeric:
        values = [float(r[k]) for r in rs if r[k]]
        result[k] = {'min': min(values), 'median': statistics.median(values),
                     'mean': statistics.mean(values), 'max': max(values)}
    return result

groups = defaultdict(list)
for r in rows:
    groups[r['account_id']].append(r)
errors = []
for i, r in enumerate(rows):
    expected_kda = (float(r['kills']) + float(r['assists'])) / max(float(r['deaths']), 1)
    for field, expected in [('kda', expected_kda),
                            ('hd_pm', float(r['hero_damage']) / float(r['dur_min'])),
                            ('lh_pm', float(r['last_hits']) / float(r['dur_min']))]:
        if abs(float(r[field]) - expected) > 1e-6:
            errors.append({'row': i, 'field': field, 'actual': r[field], 'expected': expected})

result = {
    'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'unit': 'player-match observation', 'overall': summary(rows),
    'columns': len(fields), 'missing_counts': {k: sum(not r[k] for r in rows) for k in fields},
    'label_counts': dict(Counter(r['smurf'] for r in rows)),
    'duplicate_player_match_keys': len(rows) - len({(r['match_id'], r['player_slot']) for r in rows}),
    'duplicate_account_match_keys': len(rows) - len({(r['match_id'], r['account_id']) for r in rows}),
    'duplicate_match_ids': len(rows) - len({r['match_id'] for r in rows}),
    'derived_formula_errors': errors,
    'hero_observations': dict(Counter(r['hero_id'] for r in rows)),
    'descriptive_threshold_counts': {
        'kda_gt_5': sum(float(r['kda']) > 5 for r in rows),
        'gpm_gt_700': sum(float(r['gold_per_min']) > 700 for r in rows),
        'kda_gt_5_and_gpm_gt_700': sum(float(r['kda']) > 5 and float(r['gold_per_min']) > 700 for r in rows),
        'note': 'Row-level descriptions only; not a validated smurf classifier. Total account history is unknown.'
    },
    'per_account': {k: summary(v) for k, v in sorted(groups.items())},
    'limitations': [
        'All 87 supplied observations carry smurf=1, provenance of labels is undocumented.',
        'No negative or peer control group; classification quality or prevalence cannot be estimated.',
        'Rank, tier, farm_pos, perf_z and other derived fields are entirely missing.',
        'No timestamps, match modes or objective role field. CSV period cannot be verified.',
        'Several observations belong to same account; row count is not count of independent players.',
        'Descriptive win rate only concerns this selected file; no generalization or causality.'
    ]
}
(OUT / 'smurf_profile.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'smurf_account_summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['account_id','observations','matches','wins','win_rate_pct','median_gpm','median_xpm','median_kda'])
    w.writeheader()
    for account, s in result['per_account'].items():
        w.writerow({'account_id': account, **{k:s[k] for k in ['observations','matches','wins','win_rate_pct']},
                    'median_gpm': s['gold_per_min']['median'], 'median_xpm': s['xp_per_min']['median'],
                    'median_kda': s['kda']['median']})
print(json.dumps({'overall': result['overall'], 'missing_all': [k for k,v in result['missing_counts'].items() if v==len(rows)],
                  'labels': result['label_counts'], 'duplicate_player_match_keys':result['duplicate_player_match_keys'],
                  'derived_formula_errors':len(errors)}, ensure_ascii=False, indent=2))
