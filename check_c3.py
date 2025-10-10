import csv

f = open('artifacts/em_grid.csv')
reader = csv.DictReader(f)
rows = list(reader)
f.close()

good_rows = [r for r in rows if float(r['c3']) <= 100]
print(f'Good trajectories (C3 <= 100 km^2/s^2): {len(good_rows)} out of {len(rows)}')
print(f'  Departure range: {good_rows[0]["dep_tdb"][:10]} to {good_rows[-1]["dep_tdb"][:10]}')

deps = set(r['dep_tdb'][:10] for r in good_rows)
print(f'  Departure dates with C3 <= 100: {len(deps)}')

print('\nBest 5 solutions:')
sorted_rows = sorted(rows, key=lambda r: float(r['c3']))[:5]
for r in sorted_rows:
    print(f'  Dep: {r["dep_tdb"][:10]}, TOF: {float(r["tof_days"]):3.0f}d, Arr: {r["arr_tdb"][:10]}, C3: {float(r["c3"]):6.2f} km^2/s^2')
