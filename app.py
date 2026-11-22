import pandas as pd
import streamlit as st

from engine.catalog import load_catalog
from engine.matcher import triage
from engine.ai_fallback import make_classifier
from engine.grouping import root_causes
from engine.preflight import load_northwind, preflight

st.set_page_config(page_title="Sync Doctor", page_icon="🩺", layout="wide")
st.title("Sync Doctor")
st.caption("Triage Ramp to NetSuite sync errors. Independent project, not affiliated "
           "with Ramp. Sample data is synthetic.")

AI_LIMIT = 25  # AI calls per visitor session
REQUIRED = {"object_id", "amount", "raw_error"}
EXPECTED = ["object_id", "object_type", "amount", "vendor", "ramp_entity", "date", "raw_error"]
OWNER_COLORS = {"Ramp admin": "blue", "NetSuite admin": "orange",
                "AP team": "green", "Controller": "violet"}


@st.cache_resource
def get_catalog():
    return load_catalog()


catalog = get_catalog()


def ai_enabled() -> bool:
    try:
        return bool(st.secrets.get("ANTHROPIC_API_KEY"))
    except Exception:
        return False


class AIFailed(Exception):
    """Carries a failed AI result out of the cached function without caching it."""
    def __init__(self, match):
        super().__init__(match.note)
        self.match = match


@st.cache_data(show_spinner=False)
def ai_classify(raw_error: str):
    """Cached, so the same error never costs twice."""
    m = make_classifier(catalog, st.secrets["ANTHROPIC_API_KEY"])(raw_error)
    if m.method == "ai_failed":
        raise AIFailed(m)  # cache_data never stores a raised result, so the next try is fresh
    return m


def capped_classify(raw_error: str):
    used = st.session_state.get("ai_calls", 0)
    if used >= AI_LIMIT:
        return None  # shows as unrecognized
    st.session_state["ai_calls"] = used + 1
    try:
        return ai_classify(raw_error)
    except AIFailed as e:
        return e.match  # shows as unrecognized, this time only


classify = capped_classify if ai_enabled() else None


def read_csv(source) -> pd.DataFrame:
    # Text in, like the engine: account "0610" stays "0610", and blanks are "" not NaN.
    return pd.read_csv(source, dtype=str).fillna("")


def keep_expected(df: pd.DataFrame):
    """Keep only the columns the engine reads. An uploaded 'owner' or 'id' column
    would otherwise collide with catalog columns when the two are merged."""
    ignored = [c for c in df.columns if c not in EXPECTED]
    # Missing optional columns become blank; grouping reads 'vendor', for one.
    return df.reindex(columns=EXPECTED, fill_value=""), ignored


def fix_card(row, ai_reasons=None):
    """One fix card. ai_reasons is set only for AI matches, which are suggestions, not answers."""
    with st.container(border=True):
        if not isinstance(row.get("cause"), str):
            st.warning("Not sure what this is. Contact Ramp support with the raw error.")
            return
        if ai_reasons is not None:
            # The AI's confidence didn't separate right from wrong in testing
            # (docs/ai_validation.md), so show its reasoning instead of a score.
            st.badge("AI suggestion", icon=":material/lightbulb:", color="gray")
            st.caption("No rule matched, so the AI picked the closest known cause. "
                       "Check it before acting.")
            for reason in ai_reasons:
                st.caption(f"AI's reason: {reason}")
        color = OWNER_COLORS.get(row["owner"], "gray")
        st.markdown(f"{row['category']} · Owner: :{color}[**{row['owner']}**]")
        st.write(row["cause"])
        steps = [s.strip() for s in row["fix_steps"].split("|") if s.strip()]
        st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)))
        st.link_button("Open Ramp's help article", row["ramp_url"])


def show_groups(groups, label="Failures", dollars_label="Dollars affected"):
    c1, c2, c3 = st.columns(3)
    c1.metric(label, int(groups["failures"].sum()))
    c2.metric("Root causes", len(groups))
    c3.metric(dollars_label, f"${groups['dollars'].sum():,.0f}")
    for g in groups.to_dict("records"):
        with st.expander(f"{g['failures']} · {g['headline']}"):
            fix_card(g, ai_reasons=g["notes"] if g["suggested"] else None)
            st.caption("Affected: " + ", ".join(g["object_ids"]))


tab1, tab2, tab3 = st.tabs(["Diagnose one error", "Batch triage", "Pre-flight"])

with tab1:
    raw = st.text_area("Paste a NetSuite sync error from Ramp")
    if st.button("Diagnose", type="primary") and raw.strip():
        one = triage(pd.DataFrame([{"object_id": "pasted", "amount": 0.0,
                                    "raw_error": raw}]),
                     catalog, classify=classify).iloc[0]
        is_ai = one["method"] == "ai" and isinstance(one.get("cause"), str)
        fix_card(one, ai_reasons=[one["note"]] if is_ai else None)

with tab2:
    up = st.file_uploader("Upload failed syncs (CSV)", type="csv")
    if st.button("Load Northwind sample data", key="sample_batch"):
        st.session_state["failures"] = read_csv("data/sample_failures.csv")
    if up is not None:
        st.session_state["failures"] = read_csv(up)
    if "failures" in st.session_state:
        df = st.session_state["failures"]
        missing = REQUIRED - set(df.columns)
        if missing:
            st.error(f"Your CSV is missing these columns: {', '.join(sorted(missing))}")
        else:
            df, ignored = keep_expected(df)
            if ignored:
                st.info(f"Ignored columns Sync Doctor doesn't use: {', '.join(ignored)}")
            show_groups(root_causes(triage(df, catalog, classify=classify)))

with tab3:
    st.write("Checks next month's spend against your NetSuite setup before you sync.")
    if st.button("Load Northwind sample data", key="sample_pre"):
        st.session_state["pre"] = load_northwind()
    if "pre" in st.session_state:
        issues = preflight(**st.session_state["pre"], catalog=catalog)
        if issues.empty:
            st.success("No problems found. Safe to sync.")
        else:
            show_groups(root_causes(issues), label="Predicted failures",
                        dollars_label="Dollars at risk")
