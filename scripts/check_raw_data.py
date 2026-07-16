from pathlib import Path
for folder in ['data/raw/matches', 'data/raw/rankings']:
    p = Path(folder)
    print(folder + ':')
    if p.exists():
        files = sorted(p.iterdir())
        print('  count=' + str(len(files)))
        if files:
            print('  first=' + files[0].name)
            print('  last=' + files[-1].name)
            for f in files[:3]:
                print('    ' + f.name)
    else:
        print('  MISSING')