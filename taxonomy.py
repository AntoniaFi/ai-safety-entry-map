"""Topic taxonomy for the niche finder: 30 research areas of (mostly misalignment-related) AI safety.

Each topic: label, group, phrases (used both as Semantic Scholar search terms and, turned into a regex, to assign
papers to topics from title + abstract), and optional extra regex `rx` and `need_ai` (paper must also mention
language models / AI, for phrases that occur in other fields).
"""
import re

AI_CTX = re.compile(r"\b(llms?|(large |vision[- ])?language models?|foundation models?|chatbots?|gpt(-?\w+)?|chatgpt|claude|gemini|llama|"
                    r"generative ai|genai|ai (safety|alignment|agents?|assistants?|systems?|models?|companions?|risks?|control)|"
                    r"misalign\w+|frontier (ai|models?)|transformers?|neural networks?|reinforcement learning|artificial intelligence|"
                    r"conversational (ai|agents?)|ai)\b", re.I)
STRICT = re.compile(r"\b(llms?|(large |vision[- ])?language models?|foundation models?|chatbots?|gpt(-?\w+)?|chatgpt|claude|gemini|llama|"
                    r"generative ai|genai|ai (safety|alignment|agents?|assistants?|companions?|control)|misalign\w+|frontier (ai|models?)|"
                    r"transformers?|reinforcement learning|conversational (ai|agents?)|ai models?|ai systems?)\b", re.I)
LLM = re.compile(r"\b(llms?|language models?|chatbots?|gpt(-?\w+)?|claude|gemini|llama|frontier (ai|models?)|ai (safety|alignment))\b", re.I)
HCI = {"human-oversight", "anthropomorphism-companions", "public-perception", "persuasion-manipulation", "safety-cases"}

T = {
 "emergent-misalignment": dict(label="Emergent misalignment & narrow fine-tuning", group="Model psychology",
    phrases=["emergent misalignment", "narrow finetuning", "narrow fine-tuning", "subliminal learning", "weird generalization",
             "inductive backdoor", "misalignment generalization", "emergently misaligned", "out-of-context reasoning",
             "broadly misaligned", "school of reward hacks"]),
 "personas": dict(label="Personas & model character", group="Model psychology",
    phrases=["persona vector", "persona vectors", "assistant persona", "assistant axis", "persona drift", "character training",
             "model character", "persona selection", "persona features", "simulator theory", "persona space", "model persona",
             "persona stability", "persona consistency", "LLM personas", "AI persona", "identity drift"], need_ai=True),
 "personality-psychometrics": dict(label="LLM personality & psychometrics", group="Model psychology",
    phrases=["LLM personality", "personality traits of large language models", "personality of large language models",
             "machine psychology", "psychometric evaluation of language models", "big five language models",
             "personality in LLMs", "psychometrics LLM", "dark triad language models", "LLM psychometrics"],
    rx=r"(personalit\w+|psychometric\w*|big five|big-five|dark triad|machine psychology)", need_ai=True),
 "model-organisms": dict(label="Model organisms, alignment faking & sleeper agents", group="Model psychology",
    phrases=["model organism", "model organisms", "alignment faking", "sleeper agent", "sleeper agents", "deceptive alignment",
             "hidden objective", "hidden objectives", "alignment auditing", "auditing game", "secret loyalty", "password-locked",
             "hidden goals", "auditing language models"], need_ai=True),
 "scheming-deception": dict(label="Scheming & deception evaluations", group="Model psychology",
    phrases=["scheming", "strategic deception", "in-context scheming", "deceptive behavior", "AI deception", "LLM deception",
             "lie detection", "deception detection language models", "self-preservation", "self-exfiltration", "shutdown resistance",
             "blackmail", "agentic misalignment"], need_ai=True),
 "sandbagging": dict(label="Sandbagging", group="Model psychology",
    phrases=["sandbagging", "strategic underperformance", "sandbag", "capability hiding"], need_ai=True),
 "evaluation-awareness": dict(label="Evaluation & situational awareness", group="Model psychology",
    phrases=["evaluation awareness", "situational awareness", "test awareness", "eval awareness", "evaluation-aware",
             "aware of being evaluated", "know when they are being evaluated", "observer effect", "evaluation gaming"], need_ai=True),
 "sycophancy": dict(label="Sycophancy", group="Model psychology",
    phrases=["sycophancy", "sycophantic"], need_ai=True),
 "reward-hacking": dict(label="Reward hacking & specification gaming", group="Model psychology",
    phrases=["reward hacking", "specification gaming", "reward tampering", "goal misgeneralization", "test-case hacking",
             "wireheading", "reward gaming"], need_ai=False),
 "introspection-selfknowledge": dict(label="Introspection, self-knowledge & welfare", group="Model psychology",
    phrases=["introspection language models", "introspective awareness", "self-knowledge language models", "self-recognition",
             "behavioral self-awareness", "model welfare", "AI welfare", "self-reports language models", "AI consciousness",
             "metacognition language models"],
    rx=r"(introspect\w+|self-recognition|self-awareness|model welfare|ai welfare|ai consciousness|self-reports?|metacogniti\w+|self-knowledge)", need_ai=True),
 "values-preferences": dict(label="Values, morals & preferences of models", group="Model psychology",
    phrases=["moral reasoning language models", "value alignment language models", "utility engineering", "moral judgment LLM",
             "moral dilemmas language models", "revealed preferences language models", "value systems LLM", "ethical reasoning LLM",
             "moral beliefs language models", "political bias language models"],
    rx=r"(moral (reasoning|judg\w+|dilemmas?|beliefs?|values?|foundations?)|value (alignment|systems?)|utility engineering|"
       r"revealed preferences?|stated preferences?|ethical (reasoning|dilemmas?)|political (bias|leaning|orientation))", need_ai=True),
 "machine-cognition": dict(label="Cognitive biases & theory of mind in LLMs", group="Model psychology",
    phrases=["cognitive biases language models", "theory of mind language models", "cognitive bias LLM", "human-like biases LLM",
             "anchoring bias language models", "framing effect language models"],
    rx=r"(cognitive bias\w*|theory of mind|anchoring (bias|effect)|framing effects?|decoy effect|behavio(u)?ral economics)", need_ai=True),
 "cot-monitoring": dict(label="Chain-of-thought faithfulness & monitoring", group="Oversight & control",
    phrases=["chain-of-thought faithfulness", "CoT faithfulness", "unfaithful reasoning", "chain-of-thought monitoring",
             "CoT monitoring", "monitorability", "encoded reasoning", "faithfulness of reasoning",
             "reasoning faithfulness", "unfaithful chain-of-thought", "steganographic reasoning", "steganographic chain-of-thought"],
    rx=r"((chain[- ]of[- ]thought|cot|reasoning)[^.]{0,60}(faithful\w*|unfaithful\w*|monitor\w+)|(faithful\w*|unfaithful\w*)[^.]{0,40}"
       r"(chain[- ]of[- ]thought|cot|reasoning)|monitorability|steganograph\w+[^.]{0,60}(reasoning|chain[- ]of[- ]thought|cot|monitor\w*|collu\w+|oversight)|"
       r"(reasoning|chain[- ]of[- ]thought|cot|monitor\w*|collu\w+)[^.]{0,60}steganograph\w+|encoded reasoning)", need_ai=True),
 "ai-control": dict(label="AI control & monitoring protocols", group="Oversight & control",
    phrases=["AI control", "untrusted monitoring", "trusted monitoring", "control evaluation", "control protocol", "control protocols",
             "untrusted model", "subversion strategies", "sabotage evaluations", "research sabotage"], need_ai=True),
 "scalable-oversight": dict(label="Scalable oversight, debate & weak-to-strong", group="Oversight & control",
    phrases=["scalable oversight", "AI debate", "debate protocol", "weak-to-strong", "eliciting latent knowledge",
             "debate helps", "superalignment", "weak-to-strong generalization", "LLM debate"], need_ai=True),
 "human-oversight": dict(label="Human oversight, overreliance & automation bias", group="Human–AI interaction",
    phrases=["automation bias", "overreliance on AI", "human oversight", "appropriate reliance", "human-in-the-loop oversight",
             "trust calibration", "deskilling", "cognitive forcing"], need_ai=True),
 "persuasion-manipulation": dict(label="Persuasion & manipulation by AI", group="Human–AI interaction",
    phrases=["AI persuasion", "persuasion language models", "manipulation language models", "persuasive capabilities",
             "LLM persuasion", "AI manipulation", "persuasiveness of large language models", "dark patterns LLM"],
    rx=r"(persuasi\w+|manipulative|manipulat\w+ (of )?(the )?(users?|humans?|people|beliefs?|opinions?|voters?|emotions?|decisions?)|"
       r"(psychological|emotional|social|user|opinion|belief) manipulation|dark patterns?)", need_ai=True, exclude=r"\b(robot\w*|grasp\w*|dexter\w*|manipulator|end-effector|pick[- ]and[- ]place|bimanual|embodied)\b"),
 "anthropomorphism-companions": dict(label="Anthropomorphism, companions & emotional reliance", group="Human–AI interaction",
    phrases=["anthropomorphism language models", "AI companions", "emotional reliance", "anthropomorphic AI", "parasocial AI",
             "companion chatbots", "emotional dependence chatbot", "AI psychosis", "delusion chatbot", "human-AI relationships"],
    rx=r"(anthropomorphi\w+|(ai|virtual|chatbot|digital|social) companions?|companion (chatbots?|apps?|ai|bots?)|companionship|emotional (reliance|dependence|attachment)|parasocial|ai psychosis|delusion\w*)", need_ai=True),
 "public-perception": dict(label="Public perception of AI risk (surveys)", group="Human–AI interaction",
    phrases=["public opinion artificial intelligence", "public perception of AI risk", "attitudes towards AI risk",
             "existential risk survey", "AI risk perception", "public attitudes artificial intelligence", "expert survey AI risk"],
    rx=r"((public|expert|people|citizen)s?('s)? (opinion|perceptions?|attitudes?|concerns?|support|views?|beliefs?) (of|on|about|towards?|regarding) (the )?(risks? (of|from) )?(ai|artificial intelligence|agi|advanced ai|llms?|generative ai|chatgpt|superintelligen\w+)|"
       r"(ai|artificial intelligence|agi) risk perceptions?|perceptions? of (ai|artificial intelligence) risk)", need_ai=True),
 "mech-interp": dict(label="Mechanistic interpretability (SAEs, circuits)", group="Interpretability",
    phrases=["sparse autoencoder", "sparse autoencoders", "mechanistic interpretability", "circuit discovery", "transcoder",
             "activation patching", "superposition", "attribution graph", "dictionary learning language models", "crosscoder",
             "induction heads", "automated interpretability"], need_ai=False),
 "steering-probing": dict(label="Steering vectors, probes & representation engineering", group="Interpretability",
    phrases=["steering vector", "steering vectors", "activation steering", "representation engineering", "linear probe",
             "linear probes", "refusal direction", "activation addition", "deception probes", "truth direction",
             "linear representation hypothesis", "contrastive activation addition"], need_ai=False),
 "jailbreaks-robustness": dict(label="Jailbreaks, prompt injection & red-teaming", group="Robustness & security",
    phrases=["jailbreak", "jailbreaking", "prompt injection", "adversarial suffix", "red teaming language models", "red-teaming LLM",
             "many-shot jailbreaking", "adversarial prompts"], need_ai=False),
 "backdoors-poisoning": dict(label="Backdoors & data poisoning", group="Robustness & security",
    phrases=["backdoor attack language models", "data poisoning language models", "poisoning attacks LLM", "backdoored language models",
             "trojan language models", "backdoor detection LLM"],
    rx=r"(backdoor\w*|data poisoning|poison(ed|ing) (data|samples|attack)|trojans?)", need_ai=True),
 "finetuning-unlearning": dict(label="Fine-tuning attacks, safety degradation & unlearning", group="Robustness & security",
    phrases=["harmful fine-tuning", "fine-tuning attack", "machine unlearning language models", "safety alignment degradation",
             "refusal ablation", "abliteration", "unlearning LLM", "safety guardrails fine-tuning", "tamper-resistant"],
    rx=r"(harmful fine-?tuning|fine-?tuning attacks?|unlearning|abliterat\w+|tamper[- ]resist\w+|safety (alignment|guardrails?)[^.]{0,60}fine-?tun\w+)", need_ai=True),
 "dangerous-capability-evals": dict(label="Dangerous-capability & autonomy evaluations", group="Evaluations",
    phrases=["dangerous capabilities", "autonomous replication", "self-replication", "capability evaluations frontier",
             "autonomy evaluations", "uplift study", "time horizon AI tasks", "frontier AI evaluations", "agent benchmark safety",
             "agent safety benchmark"], need_ai=True),
 "ai-rd-automation": dict(label="AI R&D automation & automated alignment research", group="Evaluations",
    phrases=["AI scientist", "automated alignment research", "AI R&D automation", "recursive self-improvement",
             "automated AI research", "research engineering benchmark", "automated AI safety research", "intelligence explosion"], need_ai=True),
 "eval-methodology": dict(label="Evaluation methodology, validity & statistics", group="Evaluations",
    phrases=["construct validity benchmark", "evaluation methodology language models", "benchmark validity", "statistics of evaluations",
             "LLM-as-a-judge reliability", "measurement validity AI", "science of evals", "evaluation reproducibility language models",
             "prompt sensitivity evaluation", "benchmark contamination"],
    rx=r"(construct validity|measurement (validity|theory)|llm[- ]as[- ]a[- ]judge|science of eval\w+|benchmark (validity|contamination|saturation)|"
       r"prompt sensitivity|statistical (rigor|rigour|significance|power)[^.]{0,60}(eval|benchmark)|(eval|benchmark)\w*[^.]{0,60}(reproducib|reliab)\w+)", need_ai=True),
 "multi-agent": dict(label="Multi-agent risks & collusion", group="Oversight & control",
    phrases=["multi-agent risks", "collusion language models", "secret collusion", "multi-agent safety", "AI collusion",
             "emergent collusion", "agent societies misalignment"],
    rx=r"(collu(sion|de|ding)|multi-agent (risks?|safety|misalignment))", need_ai=True),
 "theory-foundations": dict(label="Theory: agent foundations, corrigibility & guarantees", group="Theory",
    phrases=["corrigibility", "shutdown problem", "agent foundations", "power-seeking", "guaranteed safe AI", "singular learning theory",
             "instrumental convergence", "formal verification AI safety", "decision theory AI alignment", "mesa-optimization",
             "inner alignment"], need_ai=False),
 "safety-cases": dict(label="Safety cases & risk frameworks", group="Evaluations",
    phrases=["safety case", "safety cases", "frontier safety framework", "responsible scaling", "risk thresholds AI",
             "AI risk assessment framework", "risk management frontier AI"], need_ai=True),
}

def _phrase_rx(ph):
    parts = []
    for p in ph:
        p = re.escape(p.lower()).replace(r"\ ", r"[\s-]+").replace(r"\-", r"[\s-]?")
        parts.append(p)
    return r"\b(" + "|".join(parts) + r")"

for k, v in T.items():
    v["_rx"] = re.compile(_phrase_rx(v["phrases"]), re.I)
    v["_rx2"] = re.compile(v["rx"], re.I) if v.get("rx") else None
    v["_ex"] = re.compile(v["exclude"], re.I) if v.get("exclude") else None

def assign(title, abstract):
    """Return {topic: score}. Title hits weigh 3, abstract hits 1; the extra regex (`rx`) counts 2 / 0.5.
    A paper must mention language models or AI agents (STRICT); the human-AI interaction topics accept any AI mention."""
    title = title or ""; abstract = abstract or ""; both = title + " . " + abstract
    strict = bool(STRICT.search(both)); ai = strict or bool(AI_CTX.search(both)); out = {}
    for k, v in T.items():
        if not (strict or (ai and k in HCI)): continue
        if k == "evaluation-awareness" and not LLM.search(both): continue   # "situational awareness" is also an engineering term
        s = 3 * len(v["_rx"].findall(title)) + len(v["_rx"].findall(abstract))
        if v["_rx2"]:
            s += 2 * len(v["_rx2"].findall(title)) + 0.5 * min(4, len(v["_rx2"].findall(abstract)))
        if v.get("_ex") and s >= 1 and v["_ex"].search(title):           # e.g. robotic manipulation for the persuasion area
            s = 3 * len(v["_rx"].findall(title)) + len(v["_rx"].findall(abstract))
        if s >= 1: out[k] = s
    return out
