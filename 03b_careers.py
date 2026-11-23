"""Step 3b (23 Nov 2026): short career paths for the authors of the papers read in full (shown under each paper on the site).

For every author id in data/authorships.json whose paper was read in full, fetch the OpenAlex author record:
name and affiliation history (institution, type, country, years seen there). OpenAlex has no degrees, so
"education" here means institutions of type education; a student and a professor at the same university look alike.
Output: data/careers.json {author id: {n: name, w: works count, path: [[institution, type, first year, last year], ...]}}
Same cache and credit reserve as step 3.
"""
import importlib.util, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
spec = importlib.util.spec_from_file_location("people", os.path.join(HERE, "03_people.py")); P3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(P3)

def main():
    C = {p["id"]: p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"]}
    M = json.load(open(os.path.join(DATA, "methods.json")))
    AU = json.load(open(os.path.join(DATA, "authorships.json")))
    ids = sorted({a for pid, L in AU.items() if pid in C and C[pid]["ax"] in M for a, _ in L if a})
    print("authors of full-text papers:", len(ids), flush=True)
    out = {}
    for i in range(0, len(ids), 50):
        d = P3.get("authors", filter="openalex:" + "|".join(ids[i:i + 50]), select="id,display_name,works_count,affiliations", per_page=50)
        for a in (d or {}).get("results", []):
            path = []
            for af in a.get("affiliations") or []:
                ins = af.get("institution") or {}; ys = af.get("years") or []
                if ins.get("display_name") and ys: path.append([ins["display_name"], ins.get("type"), min(ys), max(ys)])
            path.sort(key=lambda x: (x[2], x[3]))
            out[a["id"].split("/")[-1]] = dict(n=a.get("display_name"), w=a.get("works_count"), path=path[-8:])
        if i % 2000 == 0: print(i, len(out), "credits left", P3.remaining[0], flush=True)
    json.dump(out, open(os.path.join(DATA, "careers.json"), "w"))
    print("careers", len(out), "with a path", sum(1 for v in out.values() if v["path"]), "requests", P3.calls[0])

if __name__ == "__main__":
    main()
