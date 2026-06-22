---
description: "PyAgent benchmarks — reproducible cost, quality, latency, router-savings, and compression measurements across patterns, run with a deterministic MockLLM."
---

# Benchmarks

## Methodology

Benchmarks compare all 6 pattern configurations across 4 dimensions:

- **Cost** — total tokens × model price per token
- **Latency** — wall-clock time (parallel patterns win here)
- **Quality** — keyword match score against expected outputs
- **Token efficiency** — output quality per token spent

All benchmarks use `MockLLM` for deterministic, reproducible results. Real-LLM benchmarks require `OPENAI_API_KEY`.

## Running Benchmarks

```bash
# All suites
PYTHONPATH=packages/pyagent-patterns/src:packages/pyagent-router/src:packages/pyagent-compress/src:packages/pyagent-trace/src \
  python -m benchmarks.run

# Specific suite
python -m benchmarks.run --suite cost
python -m benchmarks.run --suite quality
python -m benchmarks.run --suite latency
python -m benchmarks.run --suite router
python -m benchmarks.run --suite compression
```

## Benchmark Suites

### Cost-Effectiveness Suite

Compares token usage for identical tasks across patterns.

<!-- gen:cost_effectiveness:start (generated from data/benchmarks.yml — do not edit by hand) -->
| Pattern | Avg Tokens/Task | Avg Cost/Task | Notes |
|---------|----------------|---------------|-------|
| single_agent | 50 | $0.000100 | Baseline |
| pipeline_3stage | 150 | $0.000300 | 3× tokens, structured output |
| self_reflection | 200 | $0.000400 | 2 rounds generate+critique |
| debate | 250 | $0.000500 | 2 rounds × 2 debaters + judge |
| voting_3 | 150 | $0.000300 | 3 parallel voters |
| fanout_3 | 200 | $0.000400 | 3 parallel + aggregator |
<!-- gen:cost_effectiveness:end -->

### Quality Suite

Multi-pass patterns produce measurably higher quality.

<!-- gen:quality:start (generated from data/benchmarks.yml — do not edit by hand) -->
| Pattern | Avg Quality Score | Cost Multiplier | Quality/Cost Ratio |
|---------|------------------|----------------|--------------------|
| single_agent | 60% | 1.0× | Baseline |
| pipeline_3stage | 70% | 3.0× | 0.23× |
| self_reflection | 85% | 4.0× | 0.21× |
| debate | 80% | 5.0× | 0.16× |
| voting_3 | 75% | 3.0× | 0.25× |
| fanout_3 | 90% | 4.0× | 0.23× |
<!-- gen:quality:end -->

**Key finding:** Voting has the best quality/cost ratio — 0.25× (75% quality at 3.0× cost), since three cheap parallel voters lift quality without a reflection round. Fan-out reaches the highest _absolute_ quality (90%) for tasks with independent sub-analyses, at a slightly lower 0.23× ratio.

### Router Savings Suite

Difficulty-based routing reduces costs on mixed workloads — savings scale with how many requests fall into the cheaper tiers (the trivial-heavy mix below saves ~92%).

<!-- gen:router:start (generated from data/benchmarks.yml — do not edit by hand) -->
| Task Difficulty | Without Router | With Router | Savings |
|----------------|---------------|-------------|---------|
| Trivial (1-2) | gpt-4o ($0.003) | gpt-4.1-nano ($0.0001) | 97% |
| Easy (3-4) | gpt-4o ($0.003) | gpt-4o-mini ($0.0003) | 90% |
| Medium (5-6) | gpt-4o ($0.003) | gpt-4.1-mini ($0.001) | 67% |
| Hard (7-10) | gpt-4o ($0.003) | gpt-4o ($0.003) | 0% |
| **Mixed (70/20/10)** | **$0.003** | **$0.00023** | **92%** |
<!-- gen:router:end -->

### Compression Suite

Token compression reduces inter-agent transfer costs.

| Compression Ratio | Token Reduction | Quality Preserved | Cost Savings |
|-------------------|----------------|-------------------|-------------|
| 70% (light) | 30% | 99% | 30% |
| 50% (medium) | 50% | 95% | 50% |
| 30% (aggressive) | 70% | 85% | 70% |

**Recommended:** 50% target ratio for best quality/savings tradeoff.

## Combined Savings

Using Router + Compression together on a 5-agent pipeline:

| Configuration | Tokens | Cost | vs Baseline |
|--------------|--------|------|-------------|
| Baseline (gpt-4o, no compression) | 25,000 | $0.125 | — |
| + Router (auto-select models) | 25,000 | $0.050 | -60% |
| + Compression (50%) | 12,500 | $0.025 | -80% |
| + Both | 12,500 | $0.010 | **-92%** |
