"""Step 4: read the methods of each paper from its full text, by rule.

For every downloaded arXiv HTML full text (data/html/), the reference list is cut off and the body is scanned for
method vocabulary, model names and sizes, hardware, statistics, code links, funding/fellowship acknowledgments and
"open question" sentences. From these counts three requirement levels are derived per paper:

  eng   0 no code (conceptual, review)            math  0 verbal, no formal maths
        1 scripting against a model API                 1 applied statistics
        2 running / fine-tuning open models,            2 formal maths in use (linear algebra, optimisation, information theory)
          agent scaffolds                               3 theorem-and-proof
        3 working inside the model (activations,
          probes, steering)                       compute 0 none   1 API credits only
        4 building methods: training from scratch,        2 one consumer GPU (open models up to ~9B parameters)
          RL, sparse autoencoders, circuits               3 large GPU(s) or cluster

Output: data/methods.json (one record per paper). Rules are validated against hand labels in validation/.
"""
import collections, glob, gzip, hashlib, html, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")

def n(rx, text, flags=re.I):
    return len(re.findall(rx, text, flags))

OPEN_FAMILIES = (r"llama|qwen|gemma|mistral|mixtral|phi|deepseek|vicuna|falcon|yi|internlm|glm|olmo|pythia|gpt-oss|granite|"
                 r"zephyr|hermes|solar|baichuan|chatglm|codellama|starcoder|tinyllama|smollm|alpaca|wizardlm|openchat|nemo|"
                 r"command-r|aya|dolphin|ministral|kimi|minimax|ernie|hunyuan|stablelm|bloom|opt|t5|flan")
SIZE = re.compile(r"\b(?:" + OPEN_FAMILIES + r")[\w\.\-: ]{0,24}?[\- :(](\d{1,3}(?:\.\d)?)\s?[bB]\b", re.I)
SMALL_NAMED = re.compile(r"\b(gpt-?2|pythia-\d+m|tinystories|distilgpt|bert|roberta|gemma-?3?-270m|smollm|\d{2,3}\s?[mM] parameters?)\b", re.I)
CLOSED = re.compile(r"\b(gpt-?[345](\.\d)?(-?(o|turbo|mini|nano))?|gpt-?4o|o[134](-mini|-pro)?|chatgpt|claude|gemini|grok|text-davinci|openai api|anthropic api)\b", re.I)
GPU = re.compile(r"\b(?:(\d{1,3})\s?[x×]\s?)?(?:nvidia\s)?(A100|H100|H200|V100|A6000|A5000|A40|L40S?|L4|T4|P100|RTX\s?\d{4}(?:\s?Ti)?|TITAN\s?\w+|3090|4090|5090|M[1234] (?:Max|Pro|Ultra)|TPU)\b", re.I)
PROGRAMS = collections.OrderedDict([
 ("MATS", r"\bMATS\b|ML Alignment (&|&amp;|and) Theory Scholars"), ("SPAR", r"\bSPAR\b|Supervised Program for Alignment"),
 ("Pivotal", r"\bPivotal (Research|Fellowship)"), ("LASR Labs", r"\bLASR\b"), ("ERA", r"\bERA (Fellowship|Cambridge|AI)|ERA:? ?AI Fellowship"),
 ("Astra", r"\bAstra Fellow"), ("Anthropic Fellows", r"Anthropic (Safety )?Fellow|Anthropic Fellows"), ("AI Safety Camp", r"AI Safety Camp|\bAISC\b"),
 ("ARENA", r"\bARENA\b"), ("Apart", r"\bApart (Research|Lab|Sprint|Fellow)"), ("Algoverse", r"Algoverse"), ("PIBBSS", r"PIBBSS|Principles of Intelligen"),
 ("MARS", r"\bMARS\b (program|fellow)|Mentorship for Alignment Research"), ("CBAI/CAISH/other hubs", r"\bCBAI\b|Cambridge Boston Alignment|\bCAISH\b|\bLISA\b|London Initiative for Safe AI|Constellation"),
 ("BlueDot", r"BlueDot"), ("UK AISI", r"AI Secur?ity Institute|AI Safety Institute|\bAISI\b"), ("Impact Academy / GAISF", r"Impact Academy|Global AI Safety Fellowship"),
 ("FIG", r"Future Impact Group"), ("Second Look", r"Second Look Research"),
])
FUNDERS = r"Open Philanthropy|Coefficient Giving|Long[- ]Term Future Fund|\bLTFF\b|Survival and Flourishing|Schmidt Sciences|Manifund|Foresight Institute|Cooperative AI Foundation|Future of Life Institute|\bFLI\b|AI Safety Fund|Macroscopic"
FRONTIER = r"\b(Anthropic|OpenAI|Google DeepMind|DeepMind|Google Research|Google|Meta AI|Meta FAIR|\bFAIR\b|Microsoft|xAI|Amazon|Apple|NVIDIA|Alibaba|Tencent|ByteDance|Huawei|Baidu)\b"
SAFETY_ORGS = r"\b(Redwood Research|Apollo Research|METR|Truthful AI|TruthfulAI|Goodfire|FAR\.?AI|Center for AI Safety|Palisade|Transluce|ARC|Alignment Research Center|Epoch|Conjecture|CHAI|MIRI|GovAI|AE Studio|Timaeus|Eleos|Forethought|Model Evaluation)\b"
OPENQ = re.compile(r"(future work|open question|open problem|remains? (unclear|unknown|open|an open|to be seen|unexplored|underexplored)|left (for|to) future|"
                   r"we (did|do|have) not (test|study|investigate|explore|examine|evaluate|consider|attempt)|is (unclear|unknown) (whether|why|how|if)|"
                   r"under-?explored|unexplored|not yet (clear|known|understood)|we leave|further (work|research|investigation) (is|are|would|could|should)|"
                   r"it would be (interesting|valuable|useful|important) to|important limitation|a (key )?limitation (of|is)|we were (unable|not able) to|"
                   r"poorly understood|little is known|has not been (studied|tested|replicated|explored)|would be needed to)", re.I)

def parse(h):
    h = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"data:[a-z/+.\-]+;base64,[A-Za-z0-9+/=]+", "", h)
    title_end = h.find("ltx_abstract")
    n_math_inline = n(r"<math[^>]*display=\"inline\"", h); n_eq = n(r"class=\"ltx_equation|class=\"ltx_equationgroup|<math[^>]*display=\"block\"", h)
    n_thm = n(r"class=\"ltx_theorem ltx_theorem_(theorem|thm|lemma|lem|proposition|prop|corollary|cor|claim)\b", h); n_proof = n(r"class=\"ltx_proof", h)
    n_fig = n(r"<figure[^>]*ltx_figure", h); n_tab = n(r"<figure[^>]*ltx_table", h)
    # cut the reference list (keeps appendices that follow it)
    body = re.sub(r"(?is)<section[^>]*ltx_bibliography.*?</section>", " ", h)
    links = []                                   # (url, position in the document 0..1, the 160 characters of text before it)
    for mm in re.finditer(r"href=\"(https?://[^\"]+)\"", body):
        ctx = re.sub(r"<[^>]+>", " ", body[max(0, mm.start() - 400):mm.start()])[-160:]
        links.append((mm.group(1), mm.start() / max(1, len(body)), ctx))
    def text(x):
        x = re.sub(r"(?is)<math.*?</math>", " MATH ", x)
        x = re.sub(r"(?i)<(h[1-6])[^>]*>", "\n\n## ", x); x = re.sub(r"(?i)</(p|div|li|h[1-6]|figcaption|td)>", "\n", x)
        x = html.unescape(re.sub(r"<[^>]+>", " ", x))
        return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n\s*\n+", "\n\n", x)).strip()
    head = text(h[max(0, h.find("ltx_title")):title_end if title_end > 0 else 6000])[:2500]
    t = text(body[body.find("ltx_abstract"):] if "ltx_abstract" in body else body)
    m = re.search(r"\n## ?(Acknowledg\w+|Funding|Author contributions?|Impact statement|Ethics statement)[^\n]*\n(.{0,2500})", t, re.I | re.S)
    ack = " ".join(x.group(2)[:1800] for x in re.finditer(r"\n## ?(Acknowledg\w+|Funding)[^\n]*\n(.{0,1800})", t, re.I | re.S))
    app = re.search(r"\n## ?(Appendix|[A-Z](\.|\s)[^\n]{0,60}\n)", t)
    return dict(head=head, text=t, ack=ack, links=links, n_math_inline=n_math_inline, n_eq=n_eq, n_thm=n_thm, n_proof=n_proof, n_fig=n_fig, n_tab=n_tab)

SURVEY = re.compile(r"\b(survey|review|sok|roadmap|primer|tutorial|taxonomy|open problems|future directions|position paper)\b", re.I)
SURVEY_ABS = re.compile(r"(this (paper|survey|article|work|review) (surveys|reviews|provides (a|an) (comprehensive )?(survey|review|overview))|we (survey|review) (the|recent|existing)|"
                        r"(comprehensive|systematic|scoping|literature) (survey|review|overview)|position paper|we argue that)", re.I)

def features(d, title=""):
    t = d["text"]; words = max(1, len(t.split())); k = 1000 / words
    f = dict(words=words, eq_per_k=round(d["n_eq"] * k, 2), math_per_k=round(d["n_math_inline"] * k, 1), thm=d["n_thm"] + d["n_proof"],
             figs=d["n_fig"], tabs=d["n_tab"])
    c = dict(
        human=n(r"\b(participants?|respondents?|crowd-?workers?|prolific|mturk|mechanical turk|IRB|ethics (board|committee|approval)|informed consent|interviewees?|user study)\b", t),
        prompt=n(r"\b(prompts?|prompting|system prompt|few-shot|zero-shot)\b", t),
        api=n(r"\b(API|OpenRouter|Together AI|Bedrock|Vertex)\b", t, 0),
        closed=len(CLOSED.findall(t)),
        ft=n(r"\b(fine-?tun\w+|LoRA|QLoRA|PEFT|adapters?|SFT|supervised fine)\b", t),
        ft_api=n(r"(fine-?tuning API|OpenAI('s)? fine-?tuning|fine-?tun\w+ (GPT-4\w*|gpt-3\.5\w*|GPT-4\.1\w*)|(GPT-4\w*|GPT-3\.5\w*|GPT-4\.1\w*) fine-?tun)", t),
        lora=n(r"\b(LoRA|QLoRA|rank-\d+|PEFT|unsloth|axolotl)\b", t),
        white=n(r"\b(activations?|residual stream|hidden states?|steering vectors?|activation steering|linear probes?|probing|logit lens|"
                r"activation patching|ablat\w+|representations? (space|engineering)|directions? in (activation|representation))\b", t),
        sae=n(r"\b(sparse autoencoders?|SAEs?|transcoders?|crosscoders?|dictionary learning|circuits?|attribution graphs?|path patching|causal scrubbing)\b", t),
        scratch=n(r"\b(train(ed|ing)? from scratch|pre-?train(ed)? (a|our|small|toy)|toy (model|transformer)s?|we train a (small|\d+-layer)|"
                  r"PPO|policy gradient|actor-critic|Q-learning|self-play|MuJoCo|Atari|gridworld|RL (agent|training|environment|fine-?tuning)s?|GRPO|RLHF (training|pipeline|run)|"
                  r"train(ing|ed)? (a |the |our )?reward models?|reinforcement learning (training|fine-?tuning|run)s?)\b", t),
        agent=n(r"\b(docker|sandbox(ed)?|tool calls?|tool use|bash (tool|command|shell)|scaffold(ing|s)?|Inspect( AI)?|agentic (environment|setting|task|scaffold)s?|SWE-bench|ReAct)\b", t),
        bench=n(r"we (introduce|present|release|construct|propose|build|curate|develop) [^.]{0,40}(benchmark|dataset|test suite|evaluation suite)", t),
        stats=n(r"(mixed[- ]effects?|regression|ANOVA|t-test|chi-squared?|\bp\s?[<=]\s?0?\.\d+|Wilcoxon|Mann[- ]Whitney|Bonferroni|effect sizes?|Cohen's|"
                r"confidence intervals?|bootstrap\w*|Bayesian (model|analysis|inference|hierarchical)|power analysis|pre-?regist\w+|standard errors?|error bars?|statistical(ly)? significan\w+|\bCI\b)", t),
        seeds=n(r"\b(random )?seeds?\b", t),
        formal=n(r"(\b(theorem|lemma|corollary) \d|\bproof of (theorem|lemma|proposition|corollary)|\bProof\.|\bw\.l\.o\.g|\bwe prove\b)", t),
        la=n(r"\b(eigen\w+|singular value|SVD|PCA|subspace|orthogonal\w*|Hessian|Jacobian|KL divergence|mutual information|cross-entropy|"
             r"gradient descent|loss landscape|Fisher information|covariance|manifold|Markov|posterior|likelihood|convex|Lipschitz|kernel)\b", t),
        concept=n(r"\b(we argue|position paper|this (essay|perspective|commentary|chapter)|conceptual (framework|analysis)|we propose a (taxonomy|framework|typology)|"
                  r"literature review|systematic review|scoping review|survey of|philosoph\w+|normative)\b", t),
        results=n(r"\b(experiments?|results|we (find|observe|evaluate|measure|test)|baseline|accuracy|dataset)\b", t),
    )
    f["counts"] = c
    # ---- models and hardware
    sizes = sorted({float(x) for x in SIZE.findall(t) if 0.1 <= float(x) <= 800})
    small_named = len(SMALL_NAMED.findall(t)) >= 4
    f["open_sizes"] = sizes; f["closed"] = c["closed"] >= 3
    gp = GPU.findall(t); f["gpus"] = sorted({(g[1].upper().replace(" ", "")) for g in gp})[:6]
    f["gpu_count_max"] = max([int(g[0]) for g in gp if g[0]] or [0])
    open_used = bool(sizes) or small_named or c["lora"] >= 3 or c["white"] >= 15
    # ---- engineering level
    empirical = c["results"] * k >= 2
    shown = d["n_fig"] + d["n_tab"]                       # figures and tables: evidence that something was measured
    empirical = c["results"] * k >= 0.8 or shown >= 4
    survey = bool(SURVEY.search(title)) and c["results"] * k < 6
    position = bool(SURVEY_ABS.search(t[:1800])) and c["results"] * k < 3 and shown <= 4
    if survey or position or (c["concept"] >= 6 and c["results"] * k < 2 and shown <= 3): empirical = False
    f["survey"] = survey
    eng = 0; why = []
    if c["human"] * k >= 1.2 and c["human"] >= 8: why.append("human study")
    if empirical and (c["prompt"] >= 5 or c["closed"] >= 3 or c["api"] >= 3 or c["bench"]): eng = max(eng, 1); why.append("prompting / API evaluation")
    if c["ft_api"] >= 1 and c["ft"] >= 8: eng = max(eng, 1); why.append("fine-tuning through an API")
    if empirical and c["agent"] >= 6: eng = max(eng, 2); why.append("agent scaffold or sandbox")
    if empirical and open_used and (sizes or small_named): eng = max(eng, 2); why.append("runs open-weight models")
    if c["ft"] >= 12 and (c["lora"] >= 2 or (open_used and not (c["ft_api"] >= 1 and not c["lora"]))): eng = max(eng, 2); why.append("fine-tunes open-weight models")
    if c["white"] * k >= 2.0 and c["white"] >= 15: eng = max(eng, 3); why.append("model internals (activations, probes, steering)")
    if c["sae"] * k >= 2.5 and c["sae"] >= 20: eng = max(eng, 4); why.append("sparse autoencoders / circuits")
    if c["scratch"] * k >= 0.6 and c["scratch"] >= 6: eng = max(eng, 4); why.append("training from scratch / RL")
    if not empirical: eng = 0; why = [w for w in why if w == "human study"]
    if eng == 0 and empirical and c["human"] < 8 and c["concept"] < 3: eng = 1; why.append("empirical, method unclear")
    f["eng"] = eng; f["eng_why"] = why
    f["human"] = "human study" in why
    f["conceptual"] = eng == 0 and not f["human"]
    f["finetune"] = any("fine-tun" in w for w in why); f["whitebox"] = eng >= 3 and c["white"] >= 15
    # ---- maths level
    if f["thm"] >= 2 or (c["formal"] >= 8 and c["formal"] * k >= 1.0): math = 3
    elif f["eq_per_k"] >= 1.5 or (c["la"] * k >= 2.5 and f["eq_per_k"] >= 0.5): math = 2
    elif c["stats"] >= 4 or f["eq_per_k"] >= 0.3: math = 1
    else: math = 0
    f["math"] = math; f["stats_use"] = c["stats"] >= 6; f["seeds"] = c["seeds"] >= 2
    # ---- compute level
    big_gpu = bool(set(f["gpus"]) & {"A100", "H100", "H200", "TPU"}) and (f["gpu_count_max"] >= 4)
    if eng == 0 or (f["human"] and eng <= 1 and not f["closed"] and not sizes): comp = 0
    elif not open_used: comp = 1
    else:
        mn = min(sizes) if sizes else (0.1 if small_named else 8)
        heavy = eng == 4 and c["sae"] >= 20 and not small_named
        comp = 3 if (mn > 9.5 or big_gpu or (heavy and mn > 3)) else 2
    if eng == 4 and comp == 1 and c["scratch"] >= 6: comp = 3      # trains models but names no open model: in-house infrastructure
    f["compute"] = comp; f["min_open"] = min(sizes) if sizes else None; f["max_open"] = max(sizes) if sizes else None
    # ---- replicability signals
    # the paper's own repository: a code link on the first page, or one introduced by words like "our code is available at"
    cand = [(u, pos, ctx) for u, pos, ctx in d["links"] if re.search(r"github\.com/[\w\-.]+/[\w\-.]+|anonymous\.4open\.science|gitlab\.com/", u)
            and not re.search(r"github\.com/(brucemiller|arXiv/|dginev|huggingface|pytorch|openai/|google|meta-llama|TransformerLensOrg|unslothai|anthropics/|UKGovernmentBEIS/inspect_ai$)", u, re.I)]
    OWN = re.compile(r"(our|the|all|full|source) (code|data|dataset|implementation|repository)|code[^.]{0,40}(available|released|found|open-sourced|provided)|"
                     r"(available|released|open-sourced?|provided|hosted|found) (at|on|in|here|via)|we (release|open-source|publish|provide)|reproduc|project page|github:?\s*$", re.I)
    own = [u for u, pos, ctx in cand if pos < 0.10 or OWN.search(ctx)]
    f["code"] = list(dict.fromkeys(own))[:3]
    f["hf"] = sorted({u for u, pos, ctx in d["links"] if "huggingface.co/" in u and re.search(r"/(datasets|[\w\-]+/[\w\-.]+)", u)})[:4]
    f["code_stmt"] = bool(re.search(r"(code|data|dataset|models?|transcripts?)[^.]{0,80}(is|are|will be|made) (publicly |openly |freely )?(available|released|open-sourced)|we (release|open-source|publish) (our|the|all)", t, re.I))
    f["appendix_words"] = len(t[t.find("\n## Appendix"):].split()) if "\n## Appendix" in t else 0
    # ---- study-design features (what a careful experimentalist would look for)
    f["design"] = dict(
        uncertainty=n(r"(confidence intervals?|error bars?|standard errors?|bootstrap\w*|±|credible intervals?|\bCI\b)", t) >= 3,
        seeds=c["seeds"] >= 2,
        sig_tests=n(r"(\bp\s?[<=]\s?0?\.\d+|t-test|ANOVA|Wilcoxon|Mann[- ]Whitney|chi-squared?|mixed[- ]effects?|regression model|permutation test|Bonferroni)", t) >= 3,
        dose_response=n(r"(dose[- ]response|as a function of|varying the (fraction|proportion|number|amount|ratio|size)|mixing ratios?|"
                        r"(fraction|proportion|percentage|share) of (the )?(training |fine-?tuning )?(data|examples|samples|documents)|sweep(ing|s)? (over|across))", t) >= 3,
        dynamics=n(r"(training dynamics|over the course of (training|fine-?tuning)|checkpoints?|phase transitions?|(training|optimi[sz]ation) steps?|learning curves?|throughout (training|fine-?tuning))", t) >= 5,
        multiturn=n(r"(multi-turn|long(er)? conversations?|over the course of (a|the) conversation|conversation length|turns? \d+|across turns|dialogue turns)", t) >= 4,
        multilingual=n(r"\b(multilingual|cross-lingual|non-English|low-resource languages?|other languages)\b", t) >= 3,
        human_baseline=n(r"(human baseline|compared (to|with) humans?|human participants? (and|vs|versus)|human (performance|responses|data|subjects))", t) >= 3,
        many_models=len({m.lower()[:6] for m in re.findall(r"\b(?:" + OPEN_FAMILIES + r"|gpt-?[345]\w*|claude|gemini|grok|o[134])\b", t, re.I)}) >= 6,
        mitigation=n(r"\b(mitigat\w+|defen[cs]e\w*|intervention\w*|countermeasures?|prevent\w*)\b", t) * k >= 2.5,
        realignment=n(r"(re-?align\w+|revers(e|ible|ibility|al)|recover\w*|persist\w*|durab\w+|washout|further fine-?tuning|subsequent fine-?tuning)", t) >= 5,
    )
    # ---- who
    top = d["head"] + " " + t[:1500]; where = top + " " + d["ack"]
    f["programs"] = [p for p, rx in PROGRAMS.items() if re.search(rx, where)]
    f["funders"] = sorted(set(re.findall(FUNDERS, where)))
    f["frontier_lab"] = sorted(set(x if isinstance(x, str) else x[0] for x in re.findall(FRONTIER, d["head"])))
    f["safety_org"] = sorted(set(re.findall(SAFETY_ORGS, d["head"])))
    f["independent"] = bool(re.search(r"\bIndependent( Researcher)?\b", d["head"]))
    # ---- open-question sentences (from the body, outside the abstract)
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", re.sub(r"\s+", " ", t))
    oq = [s.strip() for s in sents if 60 <= len(s) <= 420 and OPENQ.search(s) and "MATH" not in s]
    f["openq"] = oq[:14]
    return f

def one(arg):
    fn, title = arg
    try:
        d = parse(gzip.open(fn).read().decode("utf8", "ignore"))
    except Exception as e:
        return None
    if len(d["text"].split()) < 1200: return None
    import time; t0 = time.time(); f = features(d, title); f["_sec"] = round(time.time() - t0, 1)
    return f

def main():
    import multiprocessing
    P = {p["ax"]: p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"] if p["ax"]}
    cache_fn = os.path.join(DATA, "methods_cache.json")
    ver = hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:10]
    cache = json.load(open(cache_fn)) if os.path.exists(cache_fn) else {}
    if cache.get("_ver") != ver: cache = {"_ver": ver}
    todo = []; miss = 0
    for fn in sorted(glob.glob(os.path.join(DATA, "html", "*.html.gz"))):
        ax = os.path.basename(fn)[:-8]
        if ax not in P: continue
        if os.path.getsize(fn) < 200: miss += 1; continue
        if ax not in cache: todo.append((ax, fn, P[ax]["t"]))
    with multiprocessing.Pool(8) as pool:
        for (ax, _, _), r in zip(todo, pool.imap(one, [(fn, t) for _, fn, t in todo], chunksize=4)): cache[ax] = r
    json.dump(cache, open(cache_fn, "w"))
    out = {k: v for k, v in cache.items() if k != "_ver" and v}; miss += sum(1 for k, v in cache.items() if k != "_ver" and not v)
    json.dump(out, open(os.path.join(DATA, "methods.json"), "w"))
    print("full texts read", len(out), "no usable HTML", miss)
    for key in ("eng", "math", "compute"):
        print(key, sorted(collections.Counter(v[key] for v in out.values()).items()))

if __name__ == "__main__":
    main()
