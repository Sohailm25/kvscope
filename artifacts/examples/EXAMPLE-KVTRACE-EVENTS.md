ABOUTME: Human-readable pointer to the machine-checkable kvtrace fixture.
ABOUTME: Keep the actual example in NDJSON so replay and validation tooling can consume it directly.

# Example KVTrace Events

The canonical example trace now lives in:

- [kvtrace-v2.example.ndjson](artifacts/examples/kvtrace-v2.example.ndjson)

That file illustrates:

- request lifecycle
- block lookup and hit behavior
- block insert events
- pin and unpin transitions
- eviction after the block becomes evictable
