# Growth & Funnel Insights Agent

Multi-channel funnel analysis with automated anomaly detection and AI-generated growth recommendations.

## Overview

Takes weekly funnel data across channels, computes conversion rates and ROAS at each stage, flags anomalies automatically, and generates a structured growth report with specific next-step recommendations.

## Features

- **Funnel visualization** — step-by-step drop-off from visitors through to purchase
- **Channel breakdown** — CVR, AOV, and ROAS by channel in a single view
- **WoW trend analysis** — revenue, visitor, and conversion rate trends over time
- **Anomaly detection** — rule-based flags for week-over-week drops > 15%, ROAS below threshold, and declining channel trends
- **AI growth report** — structured output: headline finding, what's working, what needs attention, 3 recommended actions

## Input format

CSV with the following columns:

| Column | Description |
|---|---|
| `week` | Week start date (YYYY-MM-DD) |
| `channel` | Traffic channel (e.g. Paid Search, Organic, Social, Email) |
| `visitors` | Sessions or unique visitors |
| `product_views` | Product page views |
| `add_to_cart` | Add-to-cart events |
| `checkout_starts` | Checkout initiations |
| `purchases` | Completed orders |
| `revenue` | Gross revenue |
| `ad_spend` | Paid spend (0 for organic channels) |

A built-in sample dataset (4 channels × 5 weeks) is included.

## Stack

| Layer | Tools |
|---|---|
| Frontend | Streamlit |
| Analysis | Pandas, NumPy |
| Visualization | Plotly (funnel, bar, line) |
| Anomaly detection | Rule-based thresholds |
| AI | DeepSeek `deepseek-chat` via OpenAI-compatible API |

## Quickstart

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_deepseek_api_key
streamlit run app.py
```

## Related

- [A/B Test Analyzer](https://github.com/josephwang-ds/ab-test-analyzer) — experiment data → significance test → verdict
- [ChatBI](https://github.com/josephwang-ds/chatbi) — natural language → SQL → results

---

[josephjwang.com](https://josephjwang.com) · [github.com/josephwang-ds](https://github.com/josephwang-ds)
