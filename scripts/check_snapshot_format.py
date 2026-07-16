import sys, json
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

snap_dir = ROOT / 'output/snapshots'
files1 = sorted(snap_dir / '000_baseline' / p for p in ['snapshot.json', 'config.json', 'snapshot_metadata.json'])
files2 = sorted(snap_dir / '001_after_group_stage_complete' / p for p in ['snapshot.json', 'config.json', 'snapshot_metadata.json'])

for label, files in [('000', files1), ('001', files2)]:
    print(f'=== {label} ===')
    for f in files:
        if f.exists():
            size = f.stat().st_size
            print(f'  {f.name}: {size} bytes')
            if size > 0 and f.name == 'snapshot.json':
                data = json.loads(f.read_text())
                print(f'    top keys: {list(data.keys())[:5]}')
                if 'model_metadata' in data:
                    print(f'    signature: {data["model_metadata"].get("signature","MISSING")}')
        else:
            print(f'  {f.name}: MISSING')
    print()