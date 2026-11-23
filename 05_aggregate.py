"""Step 5: combine corpus, people and methods into site/data.json (everything the site shows).

People appear as counts and shares per topic. Since 23 Nov 2026 the papers read in full also list their authors with a short
public career path from OpenAlex (data/careers.json, step 3b): institutions and years, first paper, earlier field.
"""
import collections, datetime, json, math, os, statistics
from taxonomy import T
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
J = lambda f: json.load(open(os.path.join(DATA, f)))
med = lambda L: round(statistics.median(L), 1) if L else None
share = lambda L: round(sum(1 for x in L if x) / len(L), 3) if L else None

def levels(m):
    """Split the old 'coding with models' level (m['eng'], 0-4) into two skills (23 Nov 2026):
    ml   working with ML models 0-4: as m['eng'], except papers whose only level-2 reason is an agent scaffold (models used through an API) -> 1
    code coding 0-3: 0 none; 1 scripts (analysis, prompting through an API); 2 software (pipelines, scaffolds, ML libraries);
         3 large systems (training from scratch / RL, cluster or 8+ GPUs)"""
    eng, why = m["eng"], m["eng_why"]
    ml = 1 if eng == 2 and not any(w in why for w in ("runs open-weight models", "fine-tunes open-weight models")) else eng
    if eng == 0: code = 1 if m["human"] and m["stats_use"] else 0
    elif eng == 1: code = 1
    else: code = 3 if (eng == 4 and "training from scratch / RL" in why) or m["compute"] == 5 or (m.get("gpu_count_max") or 0) >= 8 else 2
    return code, ml

def main():
    C = J("corpus.json"); P = [p for p in C["papers"] if p["tps"][p["tp"][0]] >= 2 or p.get("obs")]   # obs: from the Observatory Sources log (step 1b)
    M = J("methods.json"); people = J("people.json")
    val = J("validation.json") if os.path.exists(os.path.join(DATA, "validation.json")) else None
    by_paper = collections.defaultdict(list)       # paper id -> [(person, position)]
    for r in people:
        for y, t, pos, pid in r["apps"]: by_paper[pid].append((r, pos, y))
    BGS = ["Computer science / ML", "Mathematics", "Physics", "Engineering", "Natural & life sciences", "Psychology & cognitive science",
           "Social sciences, economics & law", "Philosophy & humanities"]
    AU = J("authorships.json")
    CAR = J("careers.json") if os.path.exists(os.path.join(DATA, "careers.json")) else {}
    PROF = {r["id"]: r for r in people}; used = {}
    def authors(p):
        ids = [a for a, _ in AU.get(p["id"], [])]
        if ids:
            out = []
            names = [n for _, n in p["au"]] if len(p["au"]) == len(ids) else []
            for i, a in enumerate(ids):
                c = CAR.get(a)
                if c: used[a] = c
                n = (c or {}).get("n") or (names[i] if names else None)
                if n: out.append([n, a if c else None])
            return out
        return [[n, None] for _, n in p["au"]]                      # paper id -> [[author id, [institution types]]]
    def inst_share(L, kind):
        x = [kind in types for p in L for _, types in AU.get(p["id"], []) if types]
        return share(x)
    topics = []; papers_out = []; openq = collections.defaultdict(list)
    for slug, t in T.items():
        L = [p for p in P if p["tp"][0] == slug]
        if not L: continue
        yrs = collections.Counter(p["y"] for p in L)
        F = [(p, M[p["ax"]]) for p in L if p["ax"] in M]
        f = [m for _, m in F]
        # ---- people
        firsts, alls, bg, bg_first, teams, thesis = [], [], collections.Counter(), collections.Counter(), [], []
        seen = set()
        for p in L:
            if (p["y"] or 0) < 2023: continue
            teams.append(len(p["au"]))
            for r, pos, y in by_paper.get(p["id"], []):
                age = y - r["first_pub"]
                if pos == "first":
                    firsts.append(age); bg_first[r["background"]] += 1
                    if r.get("thesis_year"): thesis.append(y - r["thesis_year"])
                if r["id"] not in seen:
                    seen.add(r["id"]); alls.append(r["entry"] - r["first_pub"]); bg[r["background"]] += 1
        known = sum(bg[b] for b in BGS); kf = sum(bg_first[b] for b in BGS)
        bgs = {b: round(bg[b] / known, 3) for b in BGS} if known else {}
        ent = -sum(v * math.log(v) for v in bgs.values() if v > 0) / math.log(len(BGS)) if bgs else None
        dsg = {k: share([m["design"][k] for m in f]) for k in (f[0]["design"] if f else {})}
        topics.append(dict(
            slug=slug, label=t["label"], group=t["group"], n=len(L), years={str(y): yrs.get(y, 0) for y in (2022, 2023, 2024, 2025, 2026)},
            n_ft=len(f), cites_median=med([p["c"] for p in L]),
            eng=[round(sum(1 for m in f if levels(m)[1] == i) / len(f), 3) for i in range(5)] if f else None,
            cod=[round(sum(1 for m in f if levels(m)[0] == i) / len(f), 3) for i in range(4)] if f else None,
            math=[round(sum(1 for m in f if m["math"] == i) / len(f), 3) for i in range(4)] if f else None,
            comp=[round(sum(1 for m in f if m["compute"] == i) / len(f), 3) for i in range(6)] if f else None,
            human=share([m["human"] for m in f]), finetune=share([m["finetune"] for m in f]), whitebox=share([m["whitebox"] for m in f]),
            code=share([bool(m["code"]) for m in f]), stats=share([m["stats_use"] for m in f]),
            program=share([bool(m["programs"]) for m in f]), frontier=share([bool(m["frontier_lab"]) for m in f]),
            closed_only=share([m["closed"] and not m["open_sizes"] for m in f]), design=dsg,
            people=dict(n=len(seen), n_first=len(firsts), first_median=med(firsts), first_new=share([a <= 1 for a in firsts]),
                        first_junior=share([a <= 3 for a in firsts]), all_median=med(alls), all_junior=share([a <= 3 for a in alls]),
                        senior=share([a > 10 for a in alls]), unknown=round(bg["No earlier papers (unknown)"] / max(1, len(seen)), 3),
                        bg=bgs, noncs=round(1 - bgs.get("Computer science / ML", 0), 3) if bgs else None,
                        evenness=round(ent, 3) if ent is not None else None, team_median=med(teams),
                        first_noncs=round(1 - bg_first["Computer science / ML"] / kf, 3) if kf else None,
                        solo=share([n <= 2 for n in teams]), company=inst_share(L, "company"), university=inst_share(L, "education"),
                        first_nonprior=round(bg_first["No earlier papers (unknown)"] / max(1, len(firsts)), 3))))
        for p, m in F:
            fa = (p["au"][0][1] if p["au"] else "?").split()[-1] + (" et al." if len(p["au"]) > 1 else "")
            papers_out.append(dict(ax=p["ax"], t=p["t"], y=p["y"], d=p["d"], a=fa, na=len(p["au"]), c=p["c"], tp=slug, tp2=p["tp"][1:],
                                   e=levels(m)[1], cd=levels(m)[0], m=m["math"], k=m["compute"], h=int(m["human"]), ft=int(m["finetune"]), wb=int(m["whitebox"]),
                                   why=m["eng_why"], code=(m["code"] or [None])[0], lo=m["min_open"], hi=m["max_open"], cl=int(m["closed"]),
                                   pr=m["programs"], lab=int(bool(m["frontier_lab"])), gpu=m["gpus"][:3],
                                   dz=[k for k, v in m["design"].items() if v], sv=int(m.get("survey", False)), au=authors(p)))
            for s in m["openq"][:6]: openq[slug].append([p["ax"], s])
    bg_all = collections.Counter(r["background"] for r in people)
    fa = [(y - r["first_pub"], r) for r in people for y, t, pos, pid in r["apps"] if pos == "first"]
    la = [y - r["first_pub"] for r in people for y, t, pos, pid in r["apps"] if pos == "last"]
    th = [y - r["thesis_year"] for r in people if r.get("thesis_year") for y, t, pos, pid in r["apps"] if pos == "first"]
    known = [r for r in people if r["background"] in BGS]
    overall = dict(first_median=med([a for a, _ in fa]), first_le1=share([a <= 1 for a, _ in fa]), first_le3=share([a <= 3 for a, _ in fa]),
                   first_gt10=share([a > 10 for a, _ in fa]), last_median=med(la), thesis_n=len(th), thesis_median=med(th),
                   thesis_before=share([x < 0 for x in th]), thesis_le3=share([0 <= x <= 3 for x in th]), thesis_gt3=share([x > 3 for x in th]),
                   known=len(known), noncs=share([r["background"] != "Computer science / ML" for r in known]),
                   bg={b: round(sum(1 for r in known if r["background"] == b) / len(known), 3) for b in BGS},
                   company=share([r.get("inst_type") == "company" for r in people if r.get("inst_type")]),
                   papers_matched=len(AU))
    print("overall", json.dumps(overall))
    INS, IDX = [], {}
    def ins(name, typ):
        k = (name, (typ or "")[:3])
        if k not in IDX: IDX[k] = len(INS); INS.append(list(k))
        return IDX[k]
    out = dict(
        meta=dict(built=datetime.date.today().isoformat(), papers=len(P), papers_all=len(C["papers"]), searched=C.get("searched"), dropped_uncited=C.get("dropped_uncited"), observatory_added=C.get("observatory_added"), fulltexts=len(papers_out),
                  people=len(people), people_bg=dict(bg_all), validation=val,
                  overall=overall, bgs=BGS),
        insts=INS, careers={a: dict(p=[[ins(x[0], x[1]), x[2], x[3]] for x in c["path"][-6:]], f=(PROF.get(a) or {}).get("first_pub"),
                         b=(PROF.get(a) or {}).get("background"), t=(PROF.get(a) or {}).get("thesis_year")) for a, c in used.items()},
        topics=topics, papers=papers_out, openq={k: v[:400] for k, v in openq.items()})
    os.makedirs(os.path.join(HERE, "site"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "site", "data.json"), "w"), separators=(",", ":"))
    print("topics", len(topics), "papers", len(P), "full texts", len(papers_out), "people", len(people),
          "size kB", os.path.getsize(os.path.join(HERE, "site", "data.json")) // 1024)
    print(f"{'topic':34s} {'n':>4s} {'ft':>4s} {'1stMed':>6s} {'new':>5s} {'nonCS':>5s} {'even':>5s} {'unk':>5s} {'prog':>5s} {'lab':>5s} {'eng<=2':>6s} {'m<=1':>5s} {'c<=2':>5s}")
    for t in sorted(topics, key=lambda t: -(t["people"]["first_new"] or 0)):
        pe = t["people"]; g = lambda v: f"{v:5.2f}" if v is not None else "    -"
        print(f"{t['slug'][:34]:34s} {t['n']:4d} {t['n_ft']:4d} {str(pe['first_median']):>6s} {g(pe['first_new'])} {g(pe['noncs'])} {g(pe['evenness'])} {g(pe['unknown'])} "
              f"{g(t['program'])} {g(t['frontier'])} {g(sum(t['eng'][:3]) if t['eng'] else None)}  {g(sum(t['math'][:2]) if t['math'] else None)} {g(sum(t['comp'][:4]) if t['comp'] else None)}")

if __name__ == "__main__":
    main()
