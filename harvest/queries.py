"""What "AI safety" covers here, written as search phrases. Two tiers:

FIELDS  the broad scope the Emerging Technology Observatory (ETO) counts: research on making AI systems work as intended
        with few adverse side effects (robustness, explainability, bias mitigation, alignment, monitoring and control,
        testing and assurance, human-AI and multi-agent coordination, deployment-context interventions).
        https://eto.tech/blog/how-we-define-ai-safety-tools/
AREAS   the 30 narrower areas of the Entry Map (taxonomy.py), mostly modes of misalignment in language models.

Each field: `strong` phrases mark a paper as in the field on their own; `weak` phrases only count together with AI context
or a second hit. Used three ways: as OpenAlex and Semantic Scholar search terms, as labelling functions, and to explain
why a paper was included.
"""
FIELDS = {
 "robustness": dict(label="Robustness: adversarial inputs, distribution shift, poisoning",
    strong=["adversarial examples", "adversarial attack", "adversarial attacks", "adversarial robustness", "adversarial training", "adversarial perturbation",
            "adversarial perturbations", "certified robustness", "robustness certification", "distribution shift", "out-of-distribution detection",
            "out-of-distribution generalization", "backdoor attack", "backdoor attacks", "backdoor defense", "backdoored", "data poisoning", "poisoning attack", "poisoning attacks", "membership inference", "model extraction", "label shift", "jailbreak", "jailbreaking",
            "prompt injection", "adversarial prompts", "robust machine learning", "covariate shift", "domain shift robustness", "model robustness"],
    weak=["robustness", "out-of-distribution", "adversarial", "corruptions", "perturbations"]),
 "explainability": dict(label="Explainability and interpretability",
    strong=["explainable ai", "explainable artificial intelligence", "xai", "interpretable machine learning", "explainability", "interpretability",
            "mechanistic interpretability", "feature attribution", "saliency map", "saliency maps", "counterfactual explanations", "post-hoc explanations",
            "sparse autoencoder", "sparse autoencoders", "concept-based explanations", "shapley", "model explanations", "explanation methods",
            "probing classifiers", "steering vector", "steering vectors", "activation steering", "representation engineering"],
    weak=["interpretable", "explanations", "attribution", "transparency"]),
 "bias-fairness": dict(label="Reducing undesired bias (implemented fairness)",
    strong=["algorithmic fairness", "fairness in machine learning", "fair machine learning", "bias mitigation", "debiasing", "fair classification",
            "demographic parity", "equalized odds", "group fairness", "individual fairness", "fairness-aware", "fairness constraints", "social bias in language models",
            "gender bias in", "mitigating bias", "bias in large language models", "stereotypical bias"],
    weak=["fairness", "biases", "disparate impact", "discrimination"]),
 "alignment": dict(label="Alignment, reward specification and misalignment",
    strong=["ai alignment", "value alignment", "alignment problem", "misalignment", "misaligned ai", "reward specification", "reward misspecification", "reward hacking",
            "specification gaming", "goal misgeneralization", "inverse reward design", "corrigibility", "deceptive alignment", "alignment faking", "emergent misalignment",
            "sycophancy", "scheming", "sandbagging", "power-seeking", "instrumental convergence", "inner alignment", "mesa-optimization", "situational awareness",
            "evaluation awareness", "model organisms of misalignment", "sleeper agents", "ai deception", "strategic deception", "safety alignment",
            "preference learning from human feedback", "constitutional ai", "scalable oversight", "weak-to-strong generalization", "eliciting latent knowledge"],
    weak=["alignment", "human values", "deception", "deceptive", "reward function", "preferences"]),
 "monitoring-control": dict(label="Monitoring and control: safe RL, shutdown, oversight, guardrails",
    strong=["safe reinforcement learning", "safe exploration", "constrained reinforcement learning", "safe rl", "ai control", "untrusted monitoring", "trusted monitoring",
            "runtime monitoring", "safety monitor", "safety shield", "shielding", "interruptibility", "shutdown problem", "human oversight", "guardrails", "content moderation of llm",
            "chain-of-thought monitoring", "failure detection", "anomaly detection for safety", "selective prediction", "learning to defer", "safe llm agents", "agent safety",
            "harmful fine-tuning", "machine unlearning", "refusal", "hallucination detection", "hallucination mitigation", "uncertainty estimation", "uncertainty quantification", "calibration of"],
    weak=["safety constraints", "oversight", "monitoring", "safe", "hallucination", "hallucinations", "calibration", "uncertainty", "toxicity", "harmful"]),
 "assurance": dict(label="Testing, evaluation, verification and assurance",
    strong=["neural network verification", "formal verification of neural networks", "verification of neural networks", "safety verification", "safety assurance",
            "assurance case", "safety case", "safety cases", "deep learning testing", "testing deep neural networks", "dnn testing", "red teaming", "red-teaming",
            "safety evaluation", "safety evaluations", "safety benchmark", "dangerous capabilities", "capability evaluations", "risk assessment of ai", "ai risk assessment",
            "safety-critical machine learning", "trustworthy ai", "trustworthy machine learning", "responsible scaling", "frontier safety", "ai auditing", "algorithmic auditing",
            "llm-as-a-judge", "construct validity"],
    weak=["safety-critical", "verification", "trustworthy", "auditing", "risk assessment", "benchmark"]),
 "human-ai": dict(label="Human-AI interaction: reliance, trust, manipulation",
    strong=["human-ai collaboration", "human-ai teaming", "human-ai interaction", "human-ai decision making", "overreliance", "over-reliance", "automation bias",
            "appropriate reliance", "trust in ai", "trust calibration", "ai persuasion", "manipulation by ai", "anthropomorphism", "ai companions", "human-in-the-loop",
            "ai-assisted decision making", "complementarity"],
    weak=["trust", "reliance", "persuasion", "manipulation", "human factors"]),
 "multi-agent": dict(label="Multi-agent coordination and cooperative AI",
    strong=["cooperative ai", "multi-agent cooperation", "multi-agent coordination", "multi-agent safety", "collusion", "social dilemmas", "ad hoc teamwork",
            "zero-shot coordination", "multi-agent risks"],
    weak=["cooperation", "coordination", "multi-agent"]),
 "general-risk": dict(label="AI safety and AI risk named directly",
    strong=["ai safety", "safe ai", "existential risk", "catastrophic risk", "catastrophic risks", "loss of control", "safety of large language models",
            "llm safety", "safe artificial intelligence", "superintelligence", "agi safety", "risks from ai", "safety of ai systems", "ai safety research"],
    weak=["safety", "risks", "harms", "ai risk", "ai risks", "responsible ai", "ai governance", "frontier ai", "beneficial ai"]),
}
# AI context: a weak phrase only counts in a text that is about machine learning systems
AI_WORDS = ["machine learning", "deep learning", "neural network", "neural networks", "language model", "language models", "llm", "llms", "reinforcement learning",
            "artificial intelligence", "ai system", "ai systems", "ai model", "ai models", "classifier", "classifiers", "transformer", "transformers", "foundation model",
            "generative ai", "chatbot", "chatbots", "ai agent", "ai agents", "autonomous agents", "deep neural", "gpt", "ai"]

# OpenAlex topics harvested in full (primary topic, 2018 on): the three that hold most of ETO's included subjects
OPENALEX_TOPICS = {"T11689": "Adversarial Robustness in Machine Learning", "T12026": "Explainable Artificial Intelligence (XAI)", "T10883": "Ethics and Social Impacts of AI"}

def all_strong():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from taxonomy import T
    out = {k: list(v["strong"]) for k, v in FIELDS.items()}
    areas = {k: list(v["phrases"]) for k, v in T.items()}
    return out, areas
