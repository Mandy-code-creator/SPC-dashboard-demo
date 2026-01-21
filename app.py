# =========================
# SIDEBAR FILTER (FIX RỖNG)
# =========================
st.sidebar.markdown("## ⏱ Time Filter")

# ---- YEAR (always from full df) ----
years = sorted(df["Year"].dropna().unique())
latest_year = int(max(years))

year = st.sidebar.selectbox(
    "Year",
    years,
    index=years.index(latest_year)
)

# ---- MONTH (from selected year, not filtered df_f) ----
months = sorted(df[df["Year"] == year]["Month"].dropna().unique())

month = st.sidebar.multiselect(
    "Month",
    months
)

# ---- APPLY TIME FILTER ----
df_f = df[df["Year"] == year]
if month:
    df_f = df_f[df_f["Month"].isin(month)]

# =========================
# COLOR CODE FILTER (SAFE)
# =========================
st.sidebar.markdown("## 🎨 Color Code")

COLOR_COL = "塗料編號"

df[COLOR_COL] = df[COLOR_COL].astype(str).str.strip()

color_codes = sorted(df_f[COLOR_COL].dropna().unique())

color = st.sidebar.selectbox(
    "Select Color Code",
    color_codes
)

df_f = df_f[df_f[COLOR_COL] == color]

# ---- EMPTY CHECK ----
if df_f.empty:
    st.warning("⚠ No data for selected filters")
    st.stop()
