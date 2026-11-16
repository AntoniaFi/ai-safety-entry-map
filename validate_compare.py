"""Compare the rule-based levels (data/methods.json) with the hand labels (validation/labels.json) -> data/validation.json
Sample A was used to adjust the rules; sample B was labelled afterwards and is the test set shown on the site."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "data", "methods.json"))); V = json.load(open(os.path.join(HERE, "validation", "labels.json")))
def score(rows):
    res = {"n": len(rows)}
    for k, top in (("eng", 4), ("math", 3), ("compute", 3)):
        pairs = [(r[k], M[r["ax"]][k]) for r in rows if r[k] is not None and r["ax"] in M]
        res[k] = dict(n=len(pairs), exact=round(sum(a == b for a, b in pairs) / len(pairs), 3), within1=round(sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs), 3),
                      reach=round(sum((a <= t) == (b <= t) for a, b in pairs for t in range(top)) / (len(pairs) * top), 3), bias=round(sum(b - a for a, b in pairs) / len(pairs), 2))
        print("  ", k, res[k], [(r["ax"], r[k], M[r["ax"]][k]) for r in rows if r[k] is not None and r["ax"] in M and r[k] != M[r["ax"]][k]])
    hp = [(r["human"], int(M[r["ax"]]["human"])) for r in rows if r["ax"] in M]
    res["human"] = dict(n=len(hp), exact=round(sum(a == b for a, b in hp) / len(hp), 3)); print("   human", res["human"])
    return res
out = {}
for s in "AB":
    print("sample", s); out[s] = score([r for r in V["labels"] if r["set"] == s])
res = dict(out["B"]); res["tuning"] = out["A"]
res["note"] = (f"One labeller (Claude), working from the abstract and five method excerpts per paper. These {out['B']['n']} papers were labelled after the main rules were set; one rule (telling reviews from experiments) was changed afterwards. "
               f"A first sample of {out['A']['n']} was used to adjust the rules (there: coding {round(out['A']['eng']['exact']*100)}%, maths {round(out['A']['math']['exact']*100)}%, compute {round(out['A']['compute']['exact']*100)}% on the same level). "
               "Reach decision: over every possible skill level, how often rule and label agree on whether the paper is within reach.")
json.dump(res, open(os.path.join(HERE, "data", "validation.json"), "w"))
