"""Example: Router — difficulty-aware model selection."""

from pyagent_router import DifficultyScorer, CostEstimator, ModelSelector
from pyagent_router.selector import Capability

def main():
    # Score difficulty
    scorer = DifficultyScorer()
    easy = scorer.score("What is 2+2?")
    hard = scorer.score("Analyze and compare the trade-offs between microservice and monolithic architectures. Design an optimal hybrid.")
    print(f"Easy: {easy.score}/10 ({easy.category})")
    print(f"Hard: {hard.score}/10 ({hard.category})")

    # Compare costs
    estimator = CostEstimator()
    estimates = estimator.compare("Explain quantum physics", models=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano"])
    print("\nCost comparison:")
    for e in estimates:
        print(f"  {e.model}: ${e.total_cost:.6f}")

    # Auto-select
    selector = ModelSelector()
    rec = selector.select("What is the capital of France?")
    print(f"\nEasy task → {rec.model}: {rec.reason}")

    rec2 = selector.select("Write a complex graph traversal algorithm", Capability.CODE)
    print(f"Hard code task → {rec2.model}: {rec2.reason}")

if __name__ == "__main__":
    main()
