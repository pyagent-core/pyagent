"""Example: Pattern Advisor — auto-select the best pattern."""

from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality, Latency

def main():
    advisor = PatternAdvisor()

    tasks = [
        ("What is 2+2?", Constraints(quality=Quality.DRAFT, latency=Latency.REALTIME)),
        ("Write a Python binary search function", Constraints(quality=Quality.HIGH)),
        ("Compare pros and cons of microservices vs monolith", Constraints(quality=Quality.HIGH)),
        ("Answer this critical safety question", Constraints(fault_tolerant=True)),
        ("Quick answer on a budget", Constraints(max_cost_usd=0.005)),
        ("Classify and route customer tickets", Constraints(multi_step=True)),
    ]

    for task, constraints in tasks:
        rec = advisor.recommend(task, constraints)
        print(f"Task: {task[:50]}...")
        print(f"  → Pattern: {rec.pattern}")
        print(f"  → Reason: {rec.reason}")
        print(f"  → Est. calls: {rec.estimated_calls}, Cost: {rec.estimated_cost_range}")
        print(f"  → Alternatives: {rec.alternatives}")
        print()

if __name__ == "__main__":
    main()
