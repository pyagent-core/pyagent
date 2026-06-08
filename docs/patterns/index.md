# Pattern Selection Guide

Use this decision tree to choose the right pattern for your task.

```mermaid
flowchart TD
    START([New Task]) --> Q1{Single step?}
    Q1 -->|Yes| Q2{Need quality check?}
    Q1 -->|No| Q3{Need classification?}
    
    Q2 -->|No| P1[Pipeline / Single Agent]
    Q2 -->|Yes| Q4{Budget tight?}
    
    Q4 -->|Yes| P2[Talker-Reasoner]
    Q4 -->|No| Q5{Adversarial needed?}
    
    Q5 -->|Yes| P3[Debate]
    Q5 -->|No| P4[Self-Reflection]
    
    Q3 -->|Yes| P5[Supervisor]
    Q3 -->|No| Q6{Parallel possible?}
    
    Q6 -->|Yes| Q7{Need consensus?}
    Q6 -->|No| P6[Pipeline]
    
    Q7 -->|Yes| P7[Fan-Out + Voting]
    Q7 -->|No| P8[Fan-Out/Fan-In]
    
    style P1 fill:#4CAF50,color:#fff
    style P2 fill:#4CAF50,color:#fff
    style P3 fill:#FF9800,color:#fff
    style P4 fill:#FF9800,color:#fff
    style P5 fill:#2196F3,color:#fff
    style P6 fill:#2196F3,color:#fff
    style P7 fill:#9C27B0,color:#fff
    style P8 fill:#9C27B0,color:#fff
```

## All 18 Patterns at a Glance

| # | Pattern | Tier | LLM Calls | Best For |
|---|---------|------|-----------|----------|
| 1 | Supervisor | Orchestration | 2-3 | Task routing, customer support |
| 2 | Pipeline | Orchestration | N stages | Sequential processing, ETL |
| 3 | Fan-Out/Fan-In | Orchestration | N+1 | Parallel analysis, research |
| 4 | Hierarchical | Orchestration | 3+ levels | Enterprise workflows |
| 5 | Orchestrator-Workers | Orchestration | 1+N+1 | Dynamic task decomposition |
| 6 | Self-Reflection | Resolution | 2-6 | Code gen, writing |
| 7 | Cross-Reflection | Resolution | 3+ | Peer review, editing |
| 8 | Debate | Resolution | D×R+1 | Controversial decisions |
| 9 | Voting | Resolution | N | Consensus, fault tolerance |
| 10 | Evaluator-Optimizer | Resolution | 2-4/round | Criteria-driven quality |
| 11 | Role-Based | Structural | N×rounds | Team simulation |
| 12 | Layered | Structural | sum(layers) | Multi-level analysis |
| 13 | Topology | Structural | varies | Communication structure |
| 14 | Blackboard | Structural | N×rounds | Shared state coordination |
| 15 | Talker-Reasoner | Advanced | 1-2 | Cost-optimized chat |
| 16 | Swarm | Advanced | N×rounds | Emergent behavior |
| 17 | Human-in-the-Loop | Advanced | 1+ | Safety-critical tasks |
| 18 | ReAct | Advanced | 1-N steps | Tool-using agents |
