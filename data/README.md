# Data

This app **does not store historical data locally**.

All pool information is fetched live from DeFiLlama’s public yields endpoint:

- https://yields.llama.fi/pools

Design goal: **APY-first, volume-optional** so the calculator remains usable even when pool volume data is missing or sparse.

