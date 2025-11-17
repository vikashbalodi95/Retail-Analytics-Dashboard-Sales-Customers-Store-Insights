# app/retail_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

st.set_page_config(page_title="Retail Store Performance", layout="wide")
st.title("Retail Store Performance Dashboard")

# --- Configuration ---
DEFAULT_CSV = Path(__file__).parents[1] / "data" / "retail_store_sample.csv"

# --- Helper functions (in-file, no utils folder) ---
def load_csv_from_path(path_or_buffer):
    df = pd.read_csv(path_or_buffer)
    # normalize column names to lowercase for flexibility
    df.columns = [c.strip() for c in df.columns]
    # expected columns (case-insensitive): date, store, category, sales, customers
    # try to auto-detect common variants
    colmap = {}
    cols_lower = [c.lower() for c in df.columns]
    if "date" in cols_lower:
        colmap["date"] = df.columns[cols_lower.index("date")]
    elif "order_date" in cols_lower:
        colmap["date"] = df.columns[cols_lower.index("order_date")]

    if "store" in cols_lower:
        colmap["store"] = df.columns[cols_lower.index("store")]
    if "category" in cols_lower:
        colmap["category"] = df.columns[cols_lower.index("category")]
    if "sales" in cols_lower or "revenue" in cols_lower:
        if "sales" in cols_lower:
            colmap["sales"] = df.columns[cols_lower.index("sales")]
        else:
            colmap["sales"] = df.columns[cols_lower.index("revenue")]
    if "customers" in cols_lower or "orders" in cols_lower:
        if "customers" in cols_lower:
            colmap["customers"] = df.columns[cols_lower.index("customers")]
        else:
            colmap["customers"] = df.columns[cols_lower.index("orders")]

    # require at least date, store, sales
    required = ["date", "store", "sales"]
    for r in required:
        if r not in colmap:
            raise ValueError(f"CSV missing required column (detected variants): {r}")

    # rename to standard names
    df = df.rename(columns={colmap[k]: k for k in colmap})
    # parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    # ensure numeric
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
    if "customers" in df.columns:
        df["customers"] = pd.to_numeric(df["customers"], errors="coerce").fillna(0)
    else:
        df["customers"] = 0
    return df

def compute_kpis(df):
    total_sales = df["sales"].sum()
    total_orders = df["customers"].sum() if df["customers"].sum() > 0 else df.shape[0]
    avg_order_value = total_sales / total_orders if total_orders else 0
    total_profit = None  # placeholder if user has profit column
    if "profit" in df.columns:
        total_profit = df["profit"].sum()
    return {
        "total_sales": total_sales,
        "total_orders": int(total_orders),
        "avg_order_value": round(avg_order_value, 2),
        "total_profit": total_profit,
    }

def monthly_sales_series(df):
    s = df.set_index("date").resample("M")["sales"].sum()
    s.index = s.index.to_period("M").to_timestamp()
    return s

def top_stores_by_sales(df, n=5):
    return df.groupby("store")["sales"].sum().sort_values(ascending=False).head(n)

# --- Sidebar: Upload or use default CSV ---
st.sidebar.header("Data")
st.sidebar.write("Upload a CSV or use the default sample file.")
uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])

use_default = False
if uploaded is None:
    if DEFAULT_CSV.exists():
        st.sidebar.write(f"Default CSV found at `{DEFAULT_CSV}`")
        use_default = st.sidebar.checkbox("Use default CSV", value=True)
    else:
        st.sidebar.info("No default CSV found. Please upload a CSV file.")

# Load dataframe
df = None
try:
    if uploaded is not None:
        df = load_csv_from_path(uploaded)
    elif use_default:
        df = load_csv_from_path(str(DEFAULT_CSV))
except Exception as e:
    st.error(f"Failed to load CSV: {e}")

if df is not None:
    st.success(f"Data loaded — {len(df):,} rows")

    # --- Quick data preview & column mapping help ---
    with st.expander("Preview & columns"):
        st.dataframe(df.head(10))
        st.write("Detected columns:", list(df.columns))

    # --- KPIs ---
    metrics = compute_kpis(df)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sales", f"₹{metrics['total_sales']:,}")
    c2.metric("Total Orders (or customers)", f"{metrics['total_orders']:,}")
    c3.metric("Avg Order Value", f"₹{metrics['avg_order_value']:,}")

    st.markdown("---")

    # --- Filters ---
    st.subheader("Filters")
    col1, col2 = st.columns([2,1])
    with col1:
        stores = st.multiselect("Stores", options=sorted(df["store"].unique()), default=sorted(df["store"].unique()))
    with col2:
        cat_default = sorted(df["category"].unique()) if "category" in df.columns else []
        categories = st.multiselect("Categories", options=cat_default, default=cat_default)

    # date filter
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    start_date, end_date = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    # apply filters
    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    mask &= df["store"].isin(stores)
    if categories:
        mask &= df["category"].isin(categories)
    dff = df.loc[mask].copy()

    st.write(f"Filtered rows: {len(dff):,}")

    # --- Sales Trend ---
    st.subheader("Sales Trend")
    freq = st.selectbox("Frequency", options=["D", "W", "M"], index=2)
    ts = dff.set_index("date").resample(freq)["sales"].sum()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ts.index, ts.values, label="Sales")
    ax.set_ylabel("Sales")
    ax.set_xlabel("Date")
    ax.legend()
    plt.xticks(rotation=30)
    st.pyplot(fig)

    # --- Moving averages ---
    st.subheader("Sales (with moving averages)")
    ts_daily = dff.set_index("date").resample("D")["sales"].sum().fillna(0)
    ma7 = ts_daily.rolling(7, min_periods=1).mean()
    ma30 = ts_daily.rolling(30, min_periods=1).mean()
    fig2, ax2 = plt.subplots(figsize=(10,4))
    ax2.plot(ts_daily.index, ts_daily.values, label="Daily Sales", alpha=0.6)
    ax2.plot(ma7.index, ma7.values, label="MA7")
    ax2.plot(ma30.index, ma30.values, label="MA30")
    ax2.legend()
    plt.xticks(rotation=30)
    st.pyplot(fig2)

    # --- Top stores ---
    st.subheader("Top Stores by Sales")
    topn = st.slider("Top N stores", 3, 10, 5)
    top_store = top_stores_by_sales(dff, n=topn)
    st.bar_chart(top_store)

    # --- Category breakdown ---
    if "category" in dff.columns:
        st.subheader("Sales by Category")
        cat_agg = dff.groupby("category")["sales"].sum().sort_values(ascending=False)
        fig3, ax3 = plt.subplots(figsize=(8,4))
        sns.barplot(x=cat_agg.values, y=cat_agg.index, ax=ax3)
        ax3.set_xlabel("Sales")
        st.pyplot(fig3)

    st.markdown("---")

    # --- Download filtered data ---
    def to_csv_bytes(df_):
        return df_.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered CSV", data=to_csv_bytes(dff), file_name="filtered_retail_data.csv", mime="text/csv")

    # --- Show raw data ---
    with st.expander("Show raw data"):
        st.dataframe(dff.sample(min(500, len(dff))))

else:
    st.info("Upload a CSV file or enable use of the default CSV in the sidebar.")
