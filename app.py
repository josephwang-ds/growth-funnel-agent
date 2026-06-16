"""
Growth & Funnel Insights Agent — Demo ⑤
Input funnel data → auto breakdown + anomaly detection + growth narrative + recommendations.

Business impact: Turns a 2-hour analyst deep-dive into a 2-minute self-serve report.
"""

import os, io, json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Growth & Funnel Agent", page_icon="🚀", layout="wide")

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background:var(--background-color); }
  [data-testid="stSidebar"] { background:var(--secondary-background-color); border-right:1px solid rgba(120,130,150,0.35); }
  [data-testid="stAppViewContainer"] .main .block-container { max-width:1220px; padding-top:1.2rem; }
  [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { font-size:16px; }
  p, label, [data-testid="stMarkdownContainer"] p { font-size:0.95rem; }
  .section-tag {
    display:inline-block;background:var(--secondary-background-color);color:var(--text-color) !important;
    border:1px solid rgba(120,130,150,0.35);
    font-size:0.76rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    padding:0.3rem 0.8rem;border-radius:4px;margin-bottom:1rem;
  }
  .stButton>button {
    background:var(--secondary-background-color);border:1px solid rgba(120,130,150,0.45);color:var(--text-color) !important;border-radius:8px;
    min-height:42px;font-weight:600;
  }
  .stButton>button:hover { border-color:var(--primary-color); }
  .stButton>button[data-testid="baseButton-primary"] { background:#4f46e5 !important;border-color:#4f46e5 !important;color:white !important; }
  .stButton>button[kind="primary"] { background:#4f46e5 !important;border-color:#4f46e5 !important;color:white !important; }
  [data-testid="stDataFrame"] { border:1px solid #334155;border-radius:8px; }
  [data-testid="stMetric"] { background:var(--secondary-background-color);border-radius:8px;padding:0.8rem 1rem; }
  [data-testid="stFileUploader"] {
    border:2px dashed rgba(120,130,150,0.45) !important;border-radius:10px !important;
    padding:1rem !important;background:var(--secondary-background-color) !important;
  }
  [data-testid="stFileUploaderDropzone"] {
    background:var(--secondary-background-color) !important;border:0 !important;
  }
  [data-testid="stFileUploaderDropzone"] * {
    color:var(--text-color) !important;
  }
  [data-testid="stDownloadButton"]>button {
    background:var(--secondary-background-color) !important;border:1px solid rgba(120,130,150,0.45) !important;
    color:var(--text-color) !important;border-radius:8px !important;min-height:42px;font-weight:600;
  }
  [data-testid="stDownloadButton"]>button:hover { border-color:var(--primary-color) !important; }
  .privacy-box {
    background:var(--secondary-background-color);border:1px solid rgba(120,130,150,0.45);border-radius:8px;
    padding:0.7rem 1rem;color:var(--text-color) !important;font-size:0.83rem;line-height:1.7;margin-bottom:1rem;
  }
  .story-box {
    background:linear-gradient(135deg,#1e1b4b 0%,#1a1f2e 100%);
    border:1px solid #4f46e5;border-radius:10px;
    padding:1rem 1.3rem;margin:0.8rem 0 1rem 0;line-height:1.8;
  }
  .leak-box {
    background:#1c1917;border:1px solid #f59e0b;border-radius:8px;
    padding:0.8rem 1.1rem;margin-top:0.6rem;
  }
  .realloc-box {
    background:#0f1f1a;border:1px solid #34d399;border-radius:8px;
    padding:0.8rem 1.1rem;margin-top:0.6rem;
  }
</style>
""", unsafe_allow_html=True)

DARK = dict(template="streamlit")
COLORS = ["#6366f1", "#06b6d4", "#34d399", "#f59e0b", "#f43f5e", "#a78bfa"]
REQUIRED_COLUMNS = {
    "week", "channel", "visitors", "product_views", "add_to_cart",
    "checkout_starts", "purchases", "revenue", "ad_spend",
}
NUMERIC_COLUMNS = [
    "visitors", "product_views", "add_to_cart", "checkout_starts",
    "purchases", "revenue", "ad_spend",
]

# ── Sample data: 8-week e-commerce story ──────────────────────────────────────
# Story arc:
#   Paid Search: spend doubled, but ROAS collapsed 7.7x → 4.2x (CPCs inflating)
#   Social: algo change hit wk3 — traffic -78%, ROAS 2.8x → 0.4x (burning money)
#   Organic: steady growth, zero cost, quietly becoming a top channel
#   Email: the hidden hero — CVR 11-13%, ROAS 100x+, massively underinvested
SAMPLE_CSV = """week,channel,visitors,product_views,add_to_cart,checkout_starts,purchases,revenue,ad_spend
2024-01-01,Paid Search,8200,3526,1023,685,254,24638,3200
2024-01-01,Organic,5100,2346,751,526,138,12420,0
2024-01-01,Social,4500,1710,342,198,59,5074,1800
2024-01-01,Email,1200,744,350,280,138,14904,150
2024-01-08,Paid Search,8700,3741,1085,727,269,26093,3450
2024-01-08,Organic,5300,2438,780,546,148,13468,0
2024-01-08,Social,3900,1482,296,172,47,3995,1750
2024-01-08,Email,1350,837,393,315,159,17331,165
2024-01-15,Paid Search,9100,3913,1135,760,274,26304,3800
2024-01-15,Organic,5600,2576,824,577,162,14742,0
2024-01-15,Social,2800,1064,213,124,28,2352,1600
2024-01-15,Email,1500,930,437,350,180,19620,180
2024-01-22,Paid Search,10200,4386,1272,853,296,28416,4800
2024-01-22,Organic,5900,2714,868,608,176,16192,0
2024-01-22,Social,2100,798,160,93,19,1577,1500
2024-01-22,Email,1700,1054,495,396,207,22770,195
2024-01-29,Paid Search,11000,4730,1372,919,308,29260,5500
2024-01-29,Organic,6100,2806,898,629,182,16744,0
2024-01-29,Social,1700,646,129,75,14,1162,1400
2024-01-29,Email,2100,1302,612,490,263,29193,215
2024-02-05,Paid Search,11400,4902,1422,953,308,28952,6000
2024-02-05,Organic,6300,2898,927,649,195,18135,0
2024-02-05,Social,1400,532,106,62,10,820,1300
2024-02-05,Email,2600,1612,758,606,331,37072,235
2024-02-12,Paid Search,11200,4816,1397,936,291,27354,6200
2024-02-12,Organic,6500,2990,957,670,201,18693,0
2024-02-12,Social,1200,456,91,53,7,567,1250
2024-02-12,Email,3100,1922,903,723,400,45200,255
2024-02-19,Paid Search,10800,4644,1347,903,270,25110,6000
2024-02-19,Organic,6700,3082,986,690,208,19552,0
2024-02-19,Social,980,372,74,43,6,480,1200
2024-02-19,Email,3800,2356,1107,886,502,57228,275
"""

# ── Core analytics functions ───────────────────────────────────────────────────

def get_client():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("⚠️ API key not configured.")
        st.stop()
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def compute_funnel_rates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["view_rate"]     = df["product_views"]   / df["visitors"]
    df["atc_rate"]      = df["add_to_cart"]      / df["product_views"]
    df["checkout_rate"] = df["checkout_starts"]  / df["add_to_cart"]
    df["purchase_rate"] = df["purchases"]        / df["checkout_starts"]
    df["overall_cvr"]   = df["purchases"]        / df["visitors"]
    df["aov"]           = df["revenue"]          / df["purchases"].replace(0, np.nan)
    df["roas"]          = np.where(df["ad_spend"] > 0, df["revenue"] / df["ad_spend"], np.nan)
    return df


def validate_input(df: pd.DataFrame) -> list[str]:
    """Return user-facing validation errors before any analysis runs."""
    errors = []
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        errors.append("Missing columns: " + ", ".join(missing))

    present_numeric = [col for col in NUMERIC_COLUMNS if col in df.columns]
    for col in present_numeric:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.isna().any():
            bad_count = int(converted.isna().sum())
            errors.append(f"{col} has {bad_count} non-numeric value(s)")
        elif (converted < 0).any():
            errors.append(f"{col} contains negative values")

    if "week" in df.columns:
        parsed = pd.to_datetime(df["week"], errors="coerce")
        if parsed.isna().any():
            errors.append("week must be parseable as a date")

    return errors


def generate_story_opener(df: pd.DataFrame) -> dict:
    """Surface the headline story: revenue trend, ROAS winner/loser, hidden hero."""
    weeks = sorted(df["week"].unique())
    if len(weeks) < 2:
        return {}

    first_rev = df[df["week"] == weeks[0]]["revenue"].sum()
    last_rev  = df[df["week"] == weeks[-1]]["revenue"].sum()
    rev_change = (last_rev - first_rev) / first_rev

    # Channel ROAS: first 2 weeks vs most recent 2 weeks.
    early = df[df["week"].isin(weeks[:2])]
    late  = df[df["week"].isin(weeks[-2:])]
    recent_window_weeks = min(2, len(weeks))

    def ch_roas(d):
        paid = d[d["ad_spend"] > 0].groupby("channel").agg(
            rev=("revenue", "sum"), spend=("ad_spend", "sum")
        )
        paid["roas"] = paid["rev"] / paid["spend"]
        return paid["roas"]

    early_roas = ch_roas(early)
    late_roas  = ch_roas(late)
    roas_change = (late_roas - early_roas).dropna()

    biggest_decliner      = roas_change.idxmin() if not roas_change.empty else None
    decliner_early_roas   = float(early_roas.get(biggest_decliner, 0)) if biggest_decliner else None
    decliner_late_roas    = float(late_roas.get(biggest_decliner, 0))  if biggest_decliner else None

    # Hero: high late ROAS but low spend share
    late_ch = late[late["ad_spend"] > 0].groupby("channel").agg(
        rev=("revenue", "sum"), spend=("ad_spend", "sum")
    ).reset_index()
    late_ch["roas"]        = late_ch["rev"] / late_ch["spend"]
    late_ch["spend_share"] = late_ch["spend"] / late_ch["spend"].sum()
    # score = ROAS_rank - spend_share_rank → highest score = most underinvested high-ROAS channel
    late_ch["score"] = late_ch["roas"].rank() - late_ch["spend_share"].rank()
    hero_row  = late_ch.loc[late_ch["score"].idxmax()]
    hero_ch   = hero_row["channel"]
    hero_recent_roas = float(hero_row["roas"])
    hero_spend_share = float(hero_row["spend_share"])

    period_paid = df[df["ad_spend"] > 0].groupby("channel").agg(
        rev=("revenue", "sum"), spend=("ad_spend", "sum")
    )
    period_paid["roas"] = period_paid["rev"] / period_paid["spend"]
    hero_period_roas = float(period_paid.loc[hero_ch, "roas"]) if hero_ch in period_paid.index else None

    return {
        "rev_change":          rev_change,
        "first_rev":           first_rev,
        "last_rev":            last_rev,
        "weeks":               len(weeks),
        "recent_window_weeks":  recent_window_weeks,
        "biggest_decliner":    biggest_decliner,
        "decliner_early_roas": decliner_early_roas,
        "decliner_late_roas":  decliner_late_roas,
        "hero_channel":        hero_ch,
        "hero_recent_roas":    hero_recent_roas,
        "hero_period_roas":    hero_period_roas,
        "hero_spend_share_pct": hero_spend_share * 100,
    }


def find_biggest_funnel_leak(df: pd.DataFrame) -> dict:
    """Find the funnel step with the highest absolute visitor drop-off."""
    steps = [
        ("Visitors → Product Views",   df["visitors"].sum(),       df["product_views"].sum()),
        ("Product Views → Add to Cart", df["product_views"].sum(), df["add_to_cart"].sum()),
        ("Add to Cart → Checkout",      df["add_to_cart"].sum(),   df["checkout_starts"].sum()),
        ("Checkout → Purchase",         df["checkout_starts"].sum(),df["purchases"].sum()),
    ]
    biggest = max(steps, key=lambda x: x[1] - x[2])
    step, from_n, to_n = biggest
    drop_pct = (from_n - to_n) / from_n
    return {"step": step, "from_n": int(from_n), "to_n": int(to_n), "drop_pct": drop_pct}


def budget_reallocation(df: pd.DataFrame) -> list[dict]:
    """
    Suggest cautious budget tests from low-ROAS to high-ROAS channels.
    Gains are scenario estimates, not guaranteed forecasts.
    """
    paid = df[df["ad_spend"] > 0].groupby("channel").agg(
        revenue=("revenue", "sum"), spend=("ad_spend", "sum")
    ).reset_index()
    paid["roas"] = paid["revenue"] / paid["spend"]
    avg_roas = paid["roas"].mean()

    underperformers = paid[paid["roas"] < avg_roas].sort_values("roas")
    overperformers  = paid[paid["roas"] > avg_roas].sort_values("roas", ascending=False)

    n_weeks = df["week"].nunique()
    suggestions = []
    for _, src in underperformers.iterrows():
        for _, dst in overperformers.iterrows():
            src_weekly_spend = src["spend"] / n_weeks
            dst_weekly_spend = dst["spend"] / n_weeks
            weekly_move = min(src_weekly_spend * 0.20, max(dst_weekly_spend * 0.50, 250), 1000)
            marginal_roas = min(dst["roas"] * 0.35, dst["roas"] - src["roas"])
            conservative_gain = weekly_move * max(marginal_roas * 0.50, 0)
            base_gain = weekly_move * max(marginal_roas * 0.75, 0)
            upside_gain = weekly_move * max(marginal_roas, 0)
            confidence = "Medium" if dst["spend"] > 0 and src["spend"] > dst["spend"] else "Low"
            suggestions.append({
                "from":            src["channel"],
                "from_roas":       round(float(src["roas"]), 1),
                "to":              dst["channel"],
                "to_roas":         round(float(dst["roas"]), 1),
                "weekly_move":     round(weekly_move),
                "gain_low":        round(conservative_gain),
                "gain_base":       round(base_gain),
                "gain_high":       round(upside_gain),
                "confidence":      confidence,
                "assumption":      "Assumes destination channel can absorb incremental spend without full-period ROAS holding constant.",
            })

    return suggestions[:3]


def detect_anomalies(df: pd.DataFrame) -> list[str]:
    flags = []
    agg = df.groupby("week").agg(
        total_revenue=("revenue", "sum"), total_visitors=("visitors", "sum"),
        total_purchases=("purchases", "sum"), total_spend=("ad_spend", "sum"),
    ).reset_index().sort_values("week")
    agg["rev_wow"] = agg["total_revenue"].pct_change()
    agg["cvr"]     = agg["total_purchases"] / agg["total_visitors"]
    agg["cvr_wow"] = agg["cvr"].pct_change()
    agg["roas"]    = agg["total_revenue"] / agg["total_spend"].replace(0, np.nan)

    for _, row in agg.iterrows():
        if pd.notna(row["rev_wow"])  and row["rev_wow"]  < -0.15:
            flags.append(f"⚠️ Week {row['week']}: Revenue dropped {row['rev_wow']:.1%} WoW")
        if pd.notna(row["cvr_wow"]) and row["cvr_wow"] < -0.10:
            flags.append(f"⚠️ Week {row['week']}: CVR dropped {row['cvr_wow']:.1%} WoW")
        if pd.notna(row["roas"])    and row["roas"] < 2:
            flags.append(f"⚠️ Week {row['week']}: Blended ROAS = {row['roas']:.1f}x — below 2x threshold")

    social = df[df["channel"] == "Social"].copy()
    if len(social) >= 2:
        first_vis = social.sort_values("week").iloc[0]["visitors"]
        last_vis  = social.sort_values("week").iloc[-1]["visitors"]
        if last_vis < first_vis * 0.8:
            flags.append(
                f"⚠️ Social traffic collapsed: {first_vis:,} → {last_vis:,} visitors "
                f"({(last_vis - first_vis) / first_vis:.0%} over {df['week'].nunique()} weeks)"
            )

    return flags if flags else ["✅ No major anomalies detected"]


def agent_narrative(client, summary: dict) -> str:
    system = """You are a senior growth analyst briefing a CMO. You have 3 minutes.

Write a narrative-first brief — not a bullet dump. Tell the story of what happened, why it matters, and what to do.

Structure (use exactly these bold headers):

**The Headline**
One sentence. The single most important thing in this data. Make it concrete: name the channel, cite the number, name the consequence.

**What the Data Is Telling Us**
2–3 short paragraphs. Walk through the story: what's growing, what's quietly breaking, and what insight the team is probably missing. Be specific. Explain causality, not just correlation. Don't hedge.

**Three Moves for Next Week**
Three actions, each on its own line. Format: [Action] → [Expected outcome with a metric].
Actions must be specific enough to assign to someone. No "consider" or "explore."

**Assumptions & Checks**
Two bullets. Separate observed facts from model assumptions. Name what the team should verify before scaling spend.

Rules: use actual numbers from the data. Do not claim causality unless the summary supports it. Treat budget_opportunities as scenario estimates, not guaranteed revenue. Write in present tense. Sound like someone who has done this before."""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": json.dumps(summary, indent=2)},
        ],
        temperature=0.4, max_tokens=700,
    )
    return resp.choices[0].message.content.strip()


# ── Charts ─────────────────────────────────────────────────────────────────────

def plot_funnel(df):
    totals = {
        "Visitors":      df["visitors"].sum(),
        "Product Views": df["product_views"].sum(),
        "Add to Cart":   df["add_to_cart"].sum(),
        "Checkout":      df["checkout_starts"].sum(),
        "Purchases":     df["purchases"].sum(),
    }
    fig = go.Figure(go.Funnel(
        y=list(totals.keys()), x=list(totals.values()),
        textinfo="value+percent previous",
        marker=dict(color=COLORS[:5]),
    ))
    fig.update_layout(title="Overall Conversion Funnel", height=350,
                      margin=dict(t=40, b=20), **DARK)
    return fig


def plot_channel_cvr(df):
    ch = df.groupby("channel").agg(
        visitors=("visitors", "sum"), purchases=("purchases", "sum")
    ).reset_index()
    ch["cvr"] = ch["purchases"] / ch["visitors"] * 100
    ch = ch.sort_values("cvr", ascending=False)
    fig = px.bar(ch, x="channel", y="cvr", color="channel",
                 title="CVR by Channel (%)",
                 text=ch["cvr"].round(1).astype(str) + "%",
                 color_discrete_sequence=COLORS)
    fig.update_layout(height=300, showlegend=False, margin=dict(t=40, b=20), **DARK)
    return fig


def plot_revenue_trend(df):
    trend = df.groupby(["week", "channel"])["revenue"].sum().reset_index()
    fig = px.line(trend, x="week", y="revenue", color="channel",
                  title="Weekly Revenue by Channel", markers=True,
                  color_discrete_sequence=COLORS)
    fig.update_layout(height=320, margin=dict(t=40, b=20), **DARK)
    return fig


def plot_roas_trend(df):
    """ROAS trend per paid channel over weeks."""
    paid = df[df["ad_spend"] > 0].copy()
    paid_trend = paid.groupby(["week", "channel"], as_index=False).agg(
        revenue=("revenue", "sum"), ad_spend=("ad_spend", "sum")
    )
    paid_trend["roas"] = paid_trend["revenue"] / paid_trend["ad_spend"]
    fig = px.line(paid_trend, x="week", y="roas", color="channel",
                  title="ROAS Trend by Channel", markers=True,
                  color_discrete_sequence=COLORS)
    fig.add_hline(y=2, line_dash="dash", line_color="#f43f5e",
                  annotation_text="2x floor", annotation_font_color="#f43f5e")
    fig.update_layout(height=320, margin=dict(t=40, b=20), **DARK)
    return fig


def plot_roas_bar(df):
    paid = df[df["ad_spend"] > 0].copy()
    ch_roas = paid.groupby("channel").apply(
        lambda x: x["revenue"].sum() / x["ad_spend"].sum()
    ).reset_index(name="roas")
    fig = px.bar(ch_roas, x="channel", y="roas", color="channel",
                 title="ROAS by Channel (full period)",
                 text=ch_roas["roas"].round(1).astype(str) + "x",
                 color_discrete_sequence=COLORS)
    fig.add_hline(y=2, line_dash="dash", line_color="#f43f5e",
                  annotation_text="2x threshold", annotation_font_color="#f43f5e")
    fig.update_layout(height=300, showlegend=False, margin=dict(t=40, b=20), **DARK)
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    lang = st.radio("语言 / Language", ["English", "中文"], horizontal=True)

    def t(en: str, zh: str) -> str:
        return zh if lang == "中文" else en

    st.markdown(f"### 🚀 {t('Growth & Funnel Agent','增长漏斗分析 Agent')}")
    st.divider()
    st.markdown(f"**{t('Required CSV columns','所需 CSV 列')}**")
    st.markdown("`week` `channel` `visitors` `product_views` `add_to_cart` `checkout_starts` `purchases` `revenue` `ad_spend`")
    st.divider()
    st.markdown(f"**{t('What this does','功能说明')}**")
    if lang == "中文":
        st.markdown(
            "- 自动检测异常与 ROAS 下滑\n"
            "- 定位漏斗最大流失点\n"
            "- 提供预算重新分配建议及预估收入影响\n"
            "- 为 CMO 生成叙述式 AI 简报\n\n"
            "2 小时分析师深度分析 → 2 分钟自助报告。"
        )
    else:
        st.markdown(
            "- Auto-detects anomalies and ROAS drops\n"
            "- Pinpoints the biggest funnel leak\n"
            "- Suggests budget reallocation with estimated revenue impact\n"
            "- Generates a narrative AI brief for the CMO\n\n"
            "2-hour analyst deep-dive → 2-minute self-serve report."
        )
    st.divider()
    if st.button(t("Reset", "重置"), width="stretch"):
        for key in ["funnel_sample", "funnel_narrative"]:
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()
    st.markdown(f"{t('Built by','作者')} [Joseph Wang](https://josephjwang.com)")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='background:linear-gradient(90deg,#6366f1,#06b6d4);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-size:2.2rem;font-weight:700;margin-bottom:0.2rem'>🚀 {t('Growth & Funnel Agent','增长漏斗分析 Agent')}</h1>
<p style='color:#94a3b8;font-size:1rem;margin-bottom:1.5rem'>
{t('Upload funnel data → auto anomaly detection · funnel leak analysis · budget reallocation · AI narrative brief',
   '上传漏斗数据 → 自动异常检测 · 漏斗流失分析 · 预算重新分配 · AI 叙述简报')}</p>
""", unsafe_allow_html=True)

# ── Step 1: Load data ──────────────────────────────────────────────────────────
st.markdown(f'<span class="section-tag">{t("Step 1 — Load funnel data","第 1 步 — 加载漏斗数据")}</span>', unsafe_allow_html=True)

mode_opts = ([t("Use sample data","使用示例数据"), t("Upload my own CSV","上传自有 CSV")])
mode = st.radio("Source", mode_opts, horizontal=True, label_visibility="collapsed")

df = None

if mode == mode_opts[0]:
    st.session_state["funnel_sample"] = True
    df = pd.read_csv(io.StringIO(SAMPLE_CSV))
    st.info(t(
        "📂 Sample: e-commerce brand, 4 channels × 8 weeks (Jan–Feb 2024). Revenue grew 79% — but the story is messier than that.",
        "📂 示例：电商品牌，4 个渠道 × 8 周（2024 年 1–2 月）。收入增长 79%——但真实故事远比数字复杂。"
    ))
else:
    st.markdown(f"""<div class="privacy-box">
    🔒 <b>{t("Your data stays private.","您的数据完全私密。")}</b> {t(
        "Uploaded files are processed in-memory for this session only — nothing is stored or logged. Closing the tab clears everything.",
        "上传文件仅在本次会话内存中处理——不存储、不记录。关闭标签页即清除所有数据。"
    )}
    </div>""", unsafe_allow_html=True)
    uploaded = st.file_uploader(t("Upload CSV","上传 CSV"), type=["csv"], label_visibility="collapsed")
    if uploaded:
        df = pd.read_csv(uploaded)
        st.success(f"✅ {t('Loaded','已加载')} {df.shape[0]:,} {t('rows','行')} × {df.shape[1]} {t('columns','列')}")
    else:
        st.markdown(f"""
        <div style="text-align:center;padding:2rem;color:#475569">
            <div style="font-size:2.5rem">📊</div>
            <p style="margin-top:0.5rem">{t("Upload your funnel CSV to get started","上传漏斗 CSV 开始分析")}</p>
        </div>""", unsafe_allow_html=True)

st.download_button(t("⬇ Download sample CSV","⬇ 下载示例 CSV"), SAMPLE_CSV.encode(), "sample_funnel.csv", "text/csv")

# ── Analysis ───────────────────────────────────────────────────────────────────
if df is not None:
    validation_errors = validate_input(df)
    if validation_errors:
        st.error(t("The uploaded CSV needs a quick fix before analysis:", "上传的 CSV 需要先修正以下问题："))
        for err in validation_errors:
            st.markdown(f"- {err}")
        st.stop()

    df["week"] = pd.to_datetime(df["week"]).dt.strftime("%Y-%m-%d")
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].apply(pd.to_numeric)
    df = compute_funnel_rates(df)

    with st.expander(t("Preview data","数据预览")):
        st.dataframe(df.head(12), width="stretch")

    # ── Story opener ───────────────────────────────────────────────────────────
    story = generate_story_opener(df)
    if story:
        rev_sign  = "+" if story["rev_change"] >= 0 else ""
        rev_color = "#34d399" if story["rev_change"] >= 0 else "#f43f5e"
        hero      = story["hero_channel"]
        hero_recent_roas = story["hero_recent_roas"]
        hero_period_roas = story["hero_period_roas"]
        hero_shr  = story["hero_spend_share_pct"]
        decliner  = story["biggest_decliner"]
        d_early   = story["decliner_early_roas"]
        d_late    = story["decliner_late_roas"]
        period_label = t(f"{story['weeks']}-Week", f"{story['weeks']} 周")
        recent_label = t(
            f"Recent {story['recent_window_weeks']}-Week",
            f"最近 {story['recent_window_weeks']} 周"
        )
        _decliner_note = (
            f" <b style='color:#f43f5e'>{decliner}</b> {t('ROAS eroded from','ROAS 从')} <b>{d_early:.1f}x → {d_late:.1f}x</b> "
            f"<span style='color:#94a3b8'>({t('early 2-week vs recent 2-week','前 2 周 vs 最近 2 周')})</span> "
            f"{t('as spend scaled — diminishing returns in play.','随投放放量而衰减——边际收益递减。')}"
            if decliner else ""
        )
        _hero_note = (
            f" {t('Meanwhile','与此同时')} <b style='color:#34d399'>{hero}</b> "
            f"{t('shows','显示')} <b>{recent_label} ROAS: {hero_recent_roas:.0f}x</b> "
            f"<span style='color:#94a3b8'>({period_label} {t('Aggregate ROAS','累计 ROAS')}: {hero_period_roas:.1f}x)</span> "
            f"{t('with only','仅占')} <b>{hero_shr:.0f}%</b> {t('of recent paid budget — the most underinvested channel in the mix.','最近付费预算——是组合中投入最少的高效渠道。')}"
            if hero else ""
        )
        st.markdown(
            f"""<div class="story-box">
            <span style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;color:#818cf8;text-transform:uppercase">
            📖 {t('Period Snapshot','区间快照')} — {story['weeks']} {t('weeks','周')}</span><br><br>
            <span style="color:#e2e8f0;font-size:0.97rem">
            {t('Revenue moved','收入变动')}
            <b style="color:{rev_color}">{rev_sign}{story['rev_change']:.0%}</b>
            {t('week-1 to week-','第 1 周至第')}{story['weeks']}{t('','周')} (${story['first_rev']:,.0f} → ${story['last_rev']:,.0f}).
            {_decliner_note}{_hero_note}
            </span>
            </div>""",
            unsafe_allow_html=True,
        )

    with st.expander(t("Agent run trace: what is deterministic vs AI-generated", "Agent 运行轨迹：哪些是确定性计算，哪些由 AI 生成")):
        st.markdown(t(
            """
1. **Validate data contract** — required columns, dates, and non-negative numeric fields.
2. **Compute metrics deterministically** — funnel rates, ROAS, AOV, CVR, channel trends.
3. **Detect anomalies with rules** — WoW drops, ROAS floors, channel collapses.
4. **Simulate budget tests** — cautious scenario ranges with explicit marginal-ROAS assumptions.
5. **Generate narrative with AI** — the model only receives the structured summary above and must separate facts from assumptions.
            """,
            """
1. **校验数据契约** — 必需字段、日期、非负数值字段。
2. **确定性计算指标** — 漏斗转化率、ROAS、AOV、CVR、渠道趋势。
3. **规则检测异常** — 环比下滑、ROAS 阈值、渠道流量崩溃。
4. **模拟预算测试** — 用谨慎情景区间表达，并显式展示边际 ROAS 假设。
5. **AI 生成叙述** — 模型只接收上方结构化摘要，并被要求区分事实与假设。
            """
        ))

    # ── Step 2: KPIs ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f'<span class="section-tag">{t("Step 2 — Period summary","第 2 步 — 区间总览")}</span>', unsafe_allow_html=True)

    total_rev    = df["revenue"].sum()
    total_vis    = df["visitors"].sum()
    total_pur    = df["purchases"].sum()
    overall_cvr  = total_pur / total_vis
    total_spend  = df["ad_spend"].sum()
    blended_roas = total_rev / total_spend if total_spend > 0 else 0
    period_label = t(f"{df['week'].nunique()}-Week", f"{df['week'].nunique()} 周")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(t("Total Revenue","总收入"),   f"${total_rev:,.0f}")
    m2.metric(t("Total Visitors","总访客数"),  f"{total_vis:,}")
    m3.metric(t("Total Purchases","总购买数"), f"{total_pur:,}")
    m4.metric(t("Overall CVR","整体转化率"),     f"{overall_cvr:.2%}")
    m5.metric(t(f"{period_label} Blended ROAS", f"{period_label} 综合 ROAS"),    f"{blended_roas:.1f}x")

    # ── Step 3: Charts ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f'<span class="section-tag">{t("Step 3 — Funnel breakdown","第 3 步 — 漏斗拆解")}</span>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(plot_funnel(df), use_container_width=True)
        # Funnel leak callout
        leak = find_biggest_funnel_leak(df)
        st.markdown(
            f"""<div class="leak-box">
            <span style="color:#f59e0b;font-weight:700;font-size:0.8rem">⚠ {t("BIGGEST FUNNEL LEAK","最大漏斗流失点")}</span><br>
            <span style="color:#e2e8f0;font-size:0.93rem">
            <b>{leak['step']}</b> — {leak['drop_pct']:.0%} {t("of visitors lost here","的访客在此流失")}
            ({leak['from_n']:,} → {leak['to_n']:,}).
            {t("This is the highest-leverage fix in the funnel.","这是漏斗中杠杆效果最高的优化点。")}
            </span></div>""",
            unsafe_allow_html=True,
        )
    with col_b:
        st.plotly_chart(plot_channel_cvr(df), use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(plot_revenue_trend(df), use_container_width=True)
    with col_d:
        st.plotly_chart(plot_roas_trend(df), use_container_width=True)

    # ── Step 4: Anomaly detection ──────────────────────────────────────────────
    st.divider()
    st.markdown(f'<span class="section-tag">{t("Step 4 — Anomaly detection","第 4 步 — 异常检测")}</span>', unsafe_allow_html=True)
    flags = detect_anomalies(df)
    for flag in flags:
        if flag.startswith("⚠️"):
            st.warning(flag)
        else:
            st.success(flag)

    action_map = []
    for flag in flags:
        text = flag.lower()
        if "revenue dropped" in text:
            action_map.append(t(
                "Revenue drop → audit top 2 channels; pause weakest campaign creative this week.",
                "收入下滑 → 审查前 2 大渠道；本周暂停效果最差的广告素材。"
            ))
        elif "cvr dropped" in text:
            action_map.append(t(
                "CVR drop → check landing page speed and checkout friction before adding spend.",
                "CVR 下滑 → 增加投放前先检查落地页速度和结账流程摩擦。"
            ))
        elif "roas" in text and "below" in text:
            action_map.append(t(
                "Low blended ROAS → cap spend on underperforming paid channels; shift to high-intent traffic.",
                "综合 ROAS 过低 → 限制低效付费渠道预算；向高意向流量倾斜。"
            ))
        elif "social" in text and "collapsed" in text:
            action_map.append(t(
                "Social traffic collapse → pause paid social; reallocate to Email or Organic amplification.",
                "社交流量崩溃 → 暂停付费社交；将预算转移至邮件或自然流量放大。"
            ))
    if action_map:
        st.markdown(f"**{t('Anomaly → Action mapping','异常 → 行动映射')}**")
        for item in action_map:
            st.markdown(f"- {item}")

    # ── Step 5: Channel table ──────────────────────────────────────────────────
    st.divider()
    st.markdown(f'<span class="section-tag">{t("Step 5 — Channel performance","第 5 步 — 渠道表现")}</span>', unsafe_allow_html=True)

    ch_summary = df.groupby("channel").agg(
        visitors=("visitors", "sum"), purchases=("purchases", "sum"),
        revenue=("revenue", "sum"), ad_spend=("ad_spend", "sum"),
    ).reset_index()
    ch_summary["cvr_%"] = (ch_summary["purchases"] / ch_summary["visitors"] * 100).round(2)
    ch_summary["aov"]   = (ch_summary["revenue"] / ch_summary["purchases"]).round(2)
    ch_summary["roas"]  = np.where(
        ch_summary["ad_spend"] > 0,
        (ch_summary["revenue"] / ch_summary["ad_spend"]).round(1), None
    )
    ch_summary["revenue_fmt"] = ch_summary["revenue"].apply(lambda x: f"${x:,.0f}")
    display_cols = ["channel", "visitors", "purchases", "cvr_%", "aov", "revenue_fmt", "ad_spend", "roas"]
    col_rename = {
        "revenue_fmt": t("revenue","收入"),
        "channel": t("channel","渠道"),
        "visitors": t("visitors","访客数"),
        "purchases": t("purchases","购买数"),
        "cvr_%": t("cvr_%","转化率_%"),
        "aov": t("aov","客单价"),
        "ad_spend": t("ad_spend","广告花费"),
        "roas": t(f"{period_label} Aggregate ROAS", f"{period_label} 累计 ROAS"),
    }
    st.dataframe(
        ch_summary[display_cols].rename(columns=col_rename),
        width="stretch",
    )

    # Budget reallocation callout
    reallocations = budget_reallocation(df)
    if reallocations:
        lines = "".join([
            f"<div style='margin-bottom:0.4rem;color:#e2e8f0;font-size:0.92rem'>"
            f"{t('Test moving','测试转移')} <b>${r['weekly_move']:,}/{t('week','周')}</b> {t('from','从')} "
            f"<b style='color:#f43f5e'>{r['from']}</b> ({period_label} {t('Aggregate ROAS','累计 ROAS')} {r['from_roas']}x) → "
            f"<b style='color:#34d399'>{r['to']}</b> ({period_label} {t('Aggregate ROAS','累计 ROAS')} {r['to_roas']}x) "
            f"<span style='color:#94a3b8'>"
            f"{t('scenario range','情景区间')}: +${r['gain_low']:,}–${r['gain_high']:,}/{t('week','周')} "
            f"({t('base','基准')} +${r['gain_base']:,}, {t('confidence','置信度')} {r['confidence']})"
            f"</span>"
            f"</div>"
            for r in reallocations
        ])
        st.markdown(
            f"""<div class="realloc-box">
            <span style="color:#34d399;font-weight:700;font-size:0.8rem">💡 {t("BUDGET REALLOCATION OPPORTUNITIES","预算重新分配机会")}</span><br><br>
            {lines}
            <div style="color:#94a3b8;font-size:0.82rem;line-height:1.6;margin-top:0.8rem">
            {t("Guardrail: these are test-budget scenarios, not guaranteed forecasts. Scale only after validating audience capacity, frequency caps, and marginal ROAS.",
               "边界条件：这些是测试预算情景，不是确定性预测。只有在验证受众容量、频控和边际 ROAS 后再扩大投放。")}
            </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Step 6: AI narrative ───────────────────────────────────────────────────
    st.divider()
    st.markdown(f'<span class="section-tag">{t("Step 6 — AI growth brief","第 6 步 — AI 增长简报")}</span>', unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#94a3b8;font-size:0.88rem;margin-bottom:0.8rem'>"
        f"{t('Generates a narrative CMO brief — headline finding, 2–3 paragraphs of story, three concrete actions with expected outcomes.','为 CMO 生成叙述式简报——核心发现、2-3 段故事、三条附带预期结果的具体行动。')}</p>",
        unsafe_allow_html=True,
    )

    if st.button(t("Generate Growth Brief","生成增长简报"), type="primary"):
        # Build rich summary for AI
        ch_data = df.groupby("channel").agg(
            visitors=("visitors", "sum"), purchases=("purchases", "sum"),
            revenue=("revenue", "sum"), ad_spend=("ad_spend", "sum"),
        ).reset_index()
        ch_data["cvr_pct"] = (ch_data["purchases"] / ch_data["visitors"] * 100).round(2)
        ch_data["period_aggregate_roas"] = (ch_data["revenue"] / ch_data["ad_spend"].replace(0, np.nan)).round(1)

        # WoW revenue trend per channel
        trend = df.groupby(["week", "channel"])["revenue"].sum().unstack(fill_value=0)
        trend_dict = {col: trend[col].tolist() for col in trend.columns}

        # ROAS trend per paid channel
        paid_df = df[df["ad_spend"] > 0].copy()
        roas_trend = paid_df.groupby(["week", "channel"], as_index=False).agg(
            revenue=("revenue", "sum"), ad_spend=("ad_spend", "sum")
        )
        roas_trend["roas"] = (roas_trend["revenue"] / roas_trend["ad_spend"]).round(1)
        roas_trend = roas_trend.pivot(index="week", columns="channel", values="roas")
        roas_trend_dict = {col: roas_trend[col].tolist() for col in roas_trend.columns}

        ch_records = [
            {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
             for k, v in rec.items()}
            for rec in ch_data.to_dict(orient="records")
        ]

        summary = {
            "period_weeks":    int(df["week"].nunique()),
            "date_range":      f"{df['week'].min()} to {df['week'].max()}",
            "totals": {
                "revenue":          float(round(total_rev)),
                "visitors":         int(total_vis),
                "purchases":        int(total_pur),
                "overall_cvr_pct":  float(round(overall_cvr * 100, 2)),
                "blended_roas":     float(round(blended_roas, 1)),
                "total_ad_spend":   float(round(total_spend)),
            },
            "by_channel":         ch_records,
            "revenue_trend_by_channel": trend_dict,
            "roas_trend_by_channel": roas_trend_dict,
            "roas_window_note": {
                "channel_table_roas": f"{df['week'].nunique()}-week aggregate ROAS",
                "story_opener_recent_roas": "Most recent 2-week aggregate ROAS",
            },
            "anomalies":          flags,
            "funnel_leak":        {
                "step":     leak["step"],
                "drop_pct": round(leak["drop_pct"] * 100, 1),
            },
            "budget_opportunities": reallocations,
            "output_contract": {
                "facts_from_code": "All metrics, anomalies, funnel leaks, and scenario ranges are computed before the LLM call.",
                "llm_role": "Turn structured facts into an executive narrative and keep assumptions explicit.",
                "guardrail": "Budget gains are scenario estimates; do not present them as guaranteed revenue.",
            },
        }

        with st.spinner(t("Analyzing your funnel…","正在分析漏斗数据…")):
            client = get_client()
            narrative = agent_narrative(client, summary)
            st.session_state["funnel_narrative"] = narrative

    if "funnel_narrative" in st.session_state:
        st.markdown(
            f"<div style='background:#1a1f2e;border:1px solid #334155;border-radius:10px;"
            f"padding:1.4rem 1.6rem;color:#e2e8f0;line-height:2;margin-top:0.5rem'>"
            f"{st.session_state['funnel_narrative'].replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )
