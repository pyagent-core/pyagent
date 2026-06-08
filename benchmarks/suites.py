"""Pre-defined benchmark suites for PyAgent patterns."""

from __future__ import annotations

from benchmarks.framework import BenchmarkSuite, BenchmarkTask

# --- Cost-Effectiveness Suite ---
COST_SUITE = BenchmarkSuite(
    name="Cost-Effectiveness",
    description="Compare token usage and cost across patterns for identical tasks",
    tasks=[
        BenchmarkTask(
            name="simple_qa",
            prompt="What is the capital of France?",
            expected_keywords=["paris"],
            max_cost_usd=0.01,
        ),
        BenchmarkTask(
            name="summarization",
            prompt="Summarize the key benefits of renewable energy in 3 bullet points",
            expected_keywords=["renewable", "energy", "solar", "wind", "clean"],
            max_cost_usd=0.02,
        ),
        BenchmarkTask(
            name="code_gen",
            prompt="Write a Python function to check if a string is a palindrome",
            expected_keywords=["def", "palindrome", "return"],
            max_cost_usd=0.03,
        ),
        BenchmarkTask(
            name="analysis",
            prompt="Analyze the pros and cons of remote work for software teams",
            expected_keywords=["remote", "productivity", "communication", "flexibility"],
            max_cost_usd=0.05,
        ),
    ],
)

# --- Quality Suite (reflection patterns should score higher) ---
QUALITY_SUITE = BenchmarkSuite(
    name="Quality",
    description="Measure output quality improvements from multi-pass patterns",
    tasks=[
        BenchmarkTask(
            name="code_review",
            prompt="Write a robust sorting function that handles edge cases: empty arrays, single elements, duplicates, negative numbers",
            expected_keywords=["def", "sort", "empty", "duplicate", "negative", "return"],
        ),
        BenchmarkTask(
            name="essay_quality",
            prompt="Write a persuasive paragraph about why testing software is important",
            expected_keywords=["testing", "bugs", "quality", "confidence", "production"],
        ),
        BenchmarkTask(
            name="data_analysis",
            prompt="Given revenue of $10M with 15% growth and 23% margins, provide a financial summary",
            expected_keywords=["10", "15", "23", "revenue", "margin", "growth"],
        ),
    ],
)

# --- Latency Suite (parallel patterns should be faster) ---
LATENCY_SUITE = BenchmarkSuite(
    name="Latency",
    description="Compare wall-clock latency: parallel vs sequential patterns",
    tasks=[
        BenchmarkTask(
            name="multi_perspective",
            prompt="Analyze this from technical, business, and user perspectives: Should we adopt microservices?",
            expected_keywords=["technical", "business", "user"],
            max_latency_seconds=5.0,
        ),
        BenchmarkTask(
            name="consensus",
            prompt="Is Python or JavaScript better for backend development? Provide a balanced answer.",
            expected_keywords=["python", "javascript"],
            max_latency_seconds=5.0,
        ),
    ],
)

# --- Router Savings Suite ---
ROUTER_SUITE = BenchmarkSuite(
    name="Router Savings",
    description="Measure cost reduction from difficulty-based model routing",
    tasks=[
        BenchmarkTask(
            name="trivial",
            prompt="What is 2+2?",
            expected_keywords=["4"],
            max_cost_usd=0.001,
        ),
        BenchmarkTask(
            name="easy",
            prompt="Explain what a variable is in programming",
            expected_keywords=["variable", "value", "store"],
            max_cost_usd=0.005,
        ),
        BenchmarkTask(
            name="medium",
            prompt="Explain the difference between TCP and UDP with use cases",
            expected_keywords=["tcp", "udp", "reliable", "connection"],
            max_cost_usd=0.01,
        ),
        BenchmarkTask(
            name="hard",
            prompt="Design a distributed consensus algorithm that handles network partitions and Byzantine faults",
            expected_keywords=["consensus", "partition", "fault", "node"],
            max_cost_usd=0.05,
        ),
    ],
)

ALL_SUITES = [COST_SUITE, QUALITY_SUITE, LATENCY_SUITE, ROUTER_SUITE]
