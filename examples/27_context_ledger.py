"""Example 27: Context ledger with trust-aware retrieval.

Demonstrates:
- Creating a ContextLedger with ContextItems
- TrustLevel and Sensitivity metadata
- TrustAwareRetriever for intelligent context selection
- ContextCompressor with semantic_lossless policy
"""

from pyagent_context import (
    ContextCompressor,
    ContextItem,
    ContextLedger,
    Sensitivity,
    TrustAwareRetriever,
    TrustLevel,
)


def main() -> None:
    ledger = ContextLedger()

    # Add context items with different trust levels
    ledger.append(ContextItem(
        content="The customer's account was created on 2024-01-15.",
        source="database",
        trust=TrustLevel.VERIFIED,
        sensitivity=Sensitivity.INTERNAL,
    ))
    ledger.append(ContextItem(
        content="The customer mentioned they prefer email communication.",
        source="agent_observation",
        trust=TrustLevel.INFERRED,
        sensitivity=Sensitivity.PUBLIC,
    ))
    ledger.append(ContextItem(
        content="Customer SSN: 123-45-6789",
        source="crm",
        trust=TrustLevel.VERIFIED,
        sensitivity=Sensitivity.PII,
    ))

    print(f"Ledger: {len(ledger)} items, {ledger.total_tokens()} est. tokens")

    # Trust-aware retrieval
    retriever = TrustAwareRetriever()
    results = retriever.retrieve(ledger.items(), query="account", top_k=2)
    print(f"\nTop 2 results for 'account':")
    for item, score in results:
        print(f"  [{item.trust}] {item.content[:60]}... (score: {score:.3f})")

    # Compression
    compressor = ContextCompressor(policy="semantic_lossless")
    compressed = compressor.compress(ledger.items(), target_tokens=50)
    print(f"\nAfter compression: {len(compressed)} items")


if __name__ == "__main__":
    main()
