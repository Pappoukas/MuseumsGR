import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# ─────────────────────────────────────────────
# Ρύθμιση σελίδας
# ─────────────────────────────────────────────
st.set_page_config(page_title="Hellenic Museums Analytics", layout="wide")

# ─────────────────────────────────────────────
# Βοηθητικές Συναρτήσεις
# ─────────────────────────────────────────────
def calculate_gini(array):
    """Υπολογισμός δείκτη Gini (0=Ισότητα, 1=Απόλυτη Ανισότητα)"""
    array = array.flatten()
    if np.any(array < 0):
        array -= np.min(array)
    array = np.sort(array + 0.000001)
    n = array.shape[0]
    index = np.arange(1, n + 1)
    return ((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))

@st.cache_data
def load_data():
    df = pd.read_csv('MuseumsGR.csv', sep=';')
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str) + '-01')
    return df

@st.cache_data
def load_places():
    import os
    if os.path.exists('museums_place_ids.csv'):
        df_p = pd.read_csv('museums_place_ids.csv')
        df_p = df_p[['Museum', 'Region', 'Place_ID', 'Google_Maps_URL', 'Rating', 'Ratings_Total', 'Address']].copy()
        df_p['Rating']        = pd.to_numeric(df_p['Rating'],        errors='coerce')
        df_p['Ratings_Total'] = pd.to_numeric(df_p['Ratings_Total'], errors='coerce')
        return df_p
    return pd.DataFrame()

def to_excel(df):
    """Μετατροπή DataFrame σε Excel bytes για download"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Δεδομένα')
    return output.getvalue()

MONTH_NAMES = {
    1: 'Ιαν', 2: 'Φεβ', 3: 'Μαρ', 4: 'Απρ',
    5: 'Μαΐ', 6: 'Ιουν', 7: 'Ιουλ', 8: 'Αυγ',
    9: 'Σεπ', 10: 'Οκτ', 11: 'Νοε', 12: 'Δεκ'
}

# ─────────────────────────────────────────────
# Φόρτωση Δεδομένων
# ─────────────────────────────────────────────
df        = load_data()
df_places = load_places()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.header("📊 Φίλτρα Ανάλυσης")

region_list = sorted(df['Region'].dropna().unique())
selected_region = st.sidebar.multiselect("Περιφέρειες", region_list, default=region_list)
df_filt = df[df['Region'].isin(selected_region)]

if 'Regional_Unit' in df.columns:
    unit_list = sorted(df_filt['Regional_Unit'].dropna().unique())
    selected_unit = st.sidebar.multiselect("Περιφερειακές Ενότητες", unit_list, default=unit_list)
    df_filt = df_filt[df_filt['Regional_Unit'].isin(selected_unit)]

museum_list = sorted(df_filt['Museum'].dropna().unique())
selected_museum = st.sidebar.selectbox("Μουσείο", ["Όλα"] + museum_list)

years = sorted(df['Year'].unique())
selected_years = st.sidebar.slider("Έτη", min(years), max(years), (2018, max(years)))

# ─────────────────────────────────────────────
# ΦΙΛΤΡΑΡΙΣΜΑ
# ─────────────────────────────────────────────
final_df = df_filt[
    (df_filt['Year'] >= selected_years[0]) &
    (df_filt['Year'] <= selected_years[1])
]
if selected_museum != "Όλα":
    final_df = final_df[final_df['Museum'] == selected_museum]

# ═════════════════════════════════════════════
# ΤΙΤΛΟΣ
# ═════════════════════════════════════════════
st.title("🏛️ Ανάλυση Επισκεψιμότητας Ελληνικών Μουσείων (1998-2025)")

# ═════════════════════════════════════════════
# 1. ADVANCED KPIs
# ═════════════════════════════════════════════
st.subheader("📊 Advanced KPIs")

total_visitors  = final_df['Visitors'].sum()
monthly_avg     = final_df['Visitors'].mean()
monthly_median  = final_df['Visitors'].median()
yearly          = final_df.groupby('Year')['Visitors'].sum()
growth          = yearly.pct_change().mean() * 100
seasonality_strength = (
    final_df.groupby('Month')['Visitors'].mean().std() / monthly_avg
    if monthly_avg > 0 else 0
)

# Συγκέντρωση: % μουσείων που συγκεντρώνουν το 80% επισκεπτών
if selected_museum == "Όλα":
    museum_totals = final_df.groupby('Museum')['Visitors'].sum().sort_values(ascending=False)
    cumsum_pct    = museum_totals.cumsum() / museum_totals.sum()
    museums_80    = (cumsum_pct <= 0.80).sum() + 1
    concentration = f"{museums_80} μουσεία → 80%"
else:
    concentration = "—"

# Γραμμή 1: Συνολικοί Επισκέπτες & Συγκέντρωση
row1_col1, row1_col2 = st.columns(2)
row1_col1.metric("Συνολικοί Επισκέπτες", f"{total_visitors:,.0f}")
row1_col2.metric("Συγκέντρωση", concentration, help="Πόσα μουσεία καλύπτουν το 80% των επισκεπτών")

# Γραμμή 2: Υπόλοιπα KPIs
row2_col1, row2_col2, row2_col3 = st.columns(3)
row2_col1.metric("Μέσος / Μήνα",         f"{monthly_avg:,.0f}")
row2_col2.metric("Διάμεσος / Μήνα",      f"{monthly_median:,.0f}")
row2_col3.metric("Μέση Ετήσια Μεταβολή", f"{growth:.2f}%")

st.divider()

# ═════════════════════════════════════════════
# 2. MUSEUM PROFILE (όταν επιλέγεται συγκεκριμένο μουσείο)
# ═════════════════════════════════════════════
if selected_museum != "Όλα":
    st.subheader(f"🏟️ Προφίλ Μουσείου: {selected_museum}")

    m_total   = final_df['Visitors'].sum()
    m_best_y  = final_df.groupby('Year')['Visitors'].sum().idxmax() if not final_df.empty else "—"
    m_worst_y = final_df.groupby('Year')['Visitors'].sum().idxmin() if not final_df.empty else "—"
    m_peak_m  = MONTH_NAMES.get(
        int(final_df.groupby('Month')['Visitors'].mean().idxmax()), "—"
    ) if not final_df.empty else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Συνολικοί Επισκέπτες", f"{m_total:,.0f}")
    c2.metric("Καλύτερο Έτος",        str(m_best_y))
    c3.metric("Χειρότερο Έτος",       str(m_worst_y))
    c4.metric("Κορυφαίος Μήνας",      m_peak_m)

    # Google Maps / Rating info
    if not df_places.empty:
        place_row = df_places[df_places['Museum'] == selected_museum]
        if not place_row.empty:
            p = place_row.iloc[0]
            st.markdown("---")
            pc1, pc2, pc3 = st.columns(3)
            rating_val = p['Rating'] if pd.notna(p['Rating']) else '—'
            reviews_val = int(p['Ratings_Total']) if pd.notna(p['Ratings_Total']) else '—'
            pc1.metric("⭐ Google Rating", f"{rating_val}/5.0")
            pc2.metric("💬 Κριτικές Google", f"{reviews_val:,}" if isinstance(reviews_val, int) else reviews_val)
            with pc3:
                if pd.notna(p['Google_Maps_URL']) and p['Google_Maps_URL'] != '':
                    st.markdown(f"[🗺️ Άνοιγμα στο Google Maps]({p['Google_Maps_URL']})")
            if pd.notna(p['Address']) and p['Address'] != '':
                st.caption(f"📍 {p['Address']}")

    # Ετήσια μπάρα για αυτό το μουσείο
    yearly_museum = final_df.groupby('Year')['Visitors'].sum().reset_index()
    fig_museum = px.bar(
        yearly_museum, x='Year', y='Visitors',
        title=f"Ετήσια Επισκεψιμότητα — {selected_museum}",
        color='Visitors', color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_museum, use_container_width=True)
    st.divider()

# ═════════════════════════════════════════════
# 3. TOP & BOTTOM MUSEUMS
# ═════════════════════════════════════════════
st.subheader("🏆 Top & Bottom Museums")
museum_rank = final_df.groupby('Museum')['Visitors'].sum().sort_values(ascending=False)

col1, col2 = st.columns(2)
with col1:
    st.write("🔝 Top 5")
    st.dataframe(museum_rank.head(5).reset_index())
with col2:
    st.write("🔻 Bottom 5")
    st.dataframe(museum_rank.tail(5).reset_index())

# ═════════════════════════════════════════════
# 4. INSIGHTS
# ═════════════════════════════════════════════
st.subheader("🧠 Insights")

if len(yearly) > 0:
    max_year   = yearly.idxmax()
    min_year   = yearly.idxmin()
    peak_month = final_df.groupby('Month')['Visitors'].mean().idxmax()
    low_month  = final_df.groupby('Month')['Visitors'].mean().idxmin()

    st.markdown(f"""
    - 📈 Peak έτος: **{max_year}**
    - 📉 Low έτος: **{min_year}**
    - ☀️ Peak μήνας: **{MONTH_NAMES.get(peak_month, peak_month)}**
    - ❄️ Low μήνας: **{MONTH_NAMES.get(low_month, low_month)}**
    - 📊 Growth: **{growth:.2f}%**
    - 📐 Διάμεσος μηνιαίων επισκεπτών: **{monthly_median:,.0f}**
    """)

# ═════════════════════════════════════════════
# 5. ΧΡΟΝΟΣΕΙΡΑ με COVID annotation & Forecast
# ═════════════════════════════════════════════
st.subheader("📈 Χρονοσειρά Επισκεψιμότητας")

trend = final_df.groupby('Date')['Visitors'].sum().reset_index()
fig_trend = px.line(trend, x='Date', y='Visitors', line_shape='spline',
                    title="Μηνιαία Επισκεψιμότητα")

# COVID annotation
fig_trend.add_vrect(
    x0="2020-03-01", x1="2021-06-01",
    fillcolor="red", opacity=0.08,
    annotation_text="COVID-19", annotation_position="top left"
)

st.plotly_chart(fig_trend, use_container_width=True)

# ═════════════════════════════════════════════
# 6. COVID IMPACT ANALYSIS
# ═════════════════════════════════════════════
st.subheader("🦠 COVID Impact Analysis")

yearly_all = df.groupby('Year')['Visitors'].sum().reset_index()
baseline   = yearly_all[yearly_all['Year'] == 2019]['Visitors'].values
if len(baseline) > 0:
    baseline_val = baseline[0]
    covid_years  = yearly_all[yearly_all['Year'].isin([2019, 2020, 2021, 2022, 2023])]
    covid_years  = covid_years.copy()
    covid_years['vs_2019_%'] = ((covid_years['Visitors'] - baseline_val) / baseline_val * 100).round(1)
    covid_years['Χρώμα'] = covid_years['vs_2019_%'].apply(
        lambda x: '🔴 Πτώση' if x < 0 else '🟢 Ανάκαμψη'
    )

    fig_covid = px.bar(
        covid_years, x='Year', y='vs_2019_%',
        color='Χρώμα',
        color_discrete_map={'🔴 Πτώση': '#e74c3c', '🟢 Ανάκαμψη': '#2ecc71'},
        title="Μεταβολή Επισκεψιμότητας σε σχέση με το 2019 (%)",
        labels={'vs_2019_%': 'Μεταβολή (%)'}
    )
    fig_covid.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_covid, use_container_width=True)

    col_rec1, col_rec2, col_rec3 = st.columns(3)
    drop_2020 = yearly_all[yearly_all['Year'] == 2020]['Visitors'].values
    rec_2022  = yearly_all[yearly_all['Year'] == 2022]['Visitors'].values
    if len(drop_2020) > 0:
        pct_drop = (drop_2020[0] - baseline_val) / baseline_val * 100
        col_rec1.metric("Πτώση 2020 vs 2019", f"{pct_drop:.1f}%")
    if len(rec_2022) > 0:
        pct_rec = (rec_2022[0] - baseline_val) / baseline_val * 100
        col_rec2.metric("Ανάκαμψη 2022 vs 2019", f"{pct_rec:+.1f}%")
    col_rec3.metric("Έτος Βάσης (2019)", f"{baseline_val:,.0f}")
else:
    st.info("Δεν υπάρχουν δεδομένα 2019 για σύγκριση.")

st.divider()

# ═════════════════════════════════════════════
# 7. HEATMAP ΈΤΟΣ × ΜΗΝΑΣ
# ═════════════════════════════════════════════
st.subheader("🔥 Heatmap Επισκεψιμότητας (Έτος × Μήνας)")

heatmap_df = (
    final_df.groupby(['Year', 'Month'])['Visitors']
    .sum()
    .reset_index()
    .pivot(index='Year', columns='Month', values='Visitors')
)
heatmap_df.columns = [MONTH_NAMES.get(c, c) for c in heatmap_df.columns]

fig_heat = px.imshow(
    heatmap_df,
    color_continuous_scale='YlOrRd',
    aspect='auto',
    title="Επισκέπτες ανά Έτος και Μήνα",
    labels=dict(x="Μήνας", y="Έτος", color="Επισκέπτες")
)
fig_heat.update_xaxes(side="bottom")
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ═════════════════════════════════════════════
# 8. YoY ΣΥΓΚΡΙΣΗ
# ═════════════════════════════════════════════
st.subheader("📅 Year-over-Year Σύγκριση")

available_years = sorted(final_df['Year'].unique())
if len(available_years) >= 2:
    col_y1, col_y2 = st.columns(2)
    with col_y1:
        yoy_year1 = st.selectbox("Έτος Α΄", available_years,
                                  index=len(available_years) - 2, key="yoy1")
    with col_y2:
        yoy_year2 = st.selectbox("Έτος Β΄", available_years,
                                  index=len(available_years) - 1, key="yoy2")

    yoy_df = (
        final_df[final_df['Year'].isin([yoy_year1, yoy_year2])]
        .groupby(['Year', 'Month'])['Visitors']
        .sum()
        .reset_index()
    )
    yoy_df['Μήνας'] = yoy_df['Month'].map(MONTH_NAMES)
    yoy_df['Έτος']  = yoy_df['Year'].astype(str)

    fig_yoy = px.bar(
        yoy_df, x='Μήνας', y='Visitors', color='Έτος',
        barmode='group',
        title=f"Μηνιαία Σύγκριση: {yoy_year1} vs {yoy_year2}",
        category_orders={'Μήνας': list(MONTH_NAMES.values())}
    )
    st.plotly_chart(fig_yoy, use_container_width=True)

    # Ποσοστιαία μεταβολή ανά μήνα
    yoy_pivot = yoy_df.pivot(index='Month', columns='Year', values='Visitors')
    if yoy_year1 in yoy_pivot.columns and yoy_year2 in yoy_pivot.columns:
        yoy_pivot['Μεταβολή (%)'] = (
            (yoy_pivot[yoy_year2] - yoy_pivot[yoy_year1]) / yoy_pivot[yoy_year1] * 100
        ).round(1)
        yoy_pivot.index = yoy_pivot.index.map(MONTH_NAMES)
        yoy_pivot.index.name = 'Μήνας'
        st.dataframe(
            yoy_pivot[[yoy_year1, yoy_year2, 'Μεταβολή (%)']].style.format({
                yoy_year1: '{:,.0f}', yoy_year2: '{:,.0f}', 'Μεταβολή (%)': '{:+.1f}%'
            }),
            use_container_width=True
        )
else:
    st.info("Απαιτούνται τουλάχιστον 2 έτη για σύγκριση.")

st.divider()

# ═════════════════════════════════════════════
# 9. ΕΠΟΧΙΚΟΤΗΤΑ & GINI
# ═════════════════════════════════════════════
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🗓️ Δείκτης Εποχικότητας")
    m_avg       = final_df.groupby('Month')['Visitors'].mean()
    overall_avg = final_df['Visitors'].mean()
    s_index     = m_avg / overall_avg
    s_index.index = s_index.index.map(MONTH_NAMES)

    fig_s = px.bar(
        x=s_index.index, y=s_index.values,
        labels={'x': 'Μήνας', 'y': 'Δείκτης'},
        title="Τιμές > 1.0 υποδηλώνουν Υψηλή Περίοδο",
        color=s_index.values, color_continuous_scale='Blues'
    )
    fig_s.add_hline(y=1.0, line_dash="dash", line_color="red",
                    annotation_text="Μέσος Όρος")
    st.plotly_chart(fig_s, use_container_width=True)

with col_right:
    st.subheader("📉 Ανάλυση Ανισότητας (Gini)")
    if selected_museum == "Όλα":
        dist  = final_df.groupby('Museum')['Visitors'].sum().values
        g_val = calculate_gini(dist)
        st.metric("Δείκτης Gini", f"{g_val:.3f}")
        st.caption("0 = Ισοκατανομή | 1 = Συγκέντρωση σε λίγα μουσεία")

        sorted_dist = np.sort(dist)
        lorenz      = np.cumsum(sorted_dist) / np.sum(sorted_dist)
        fig_l = px.area(
            x=np.linspace(0, 1, len(lorenz)), y=lorenz,
            title="Καμπύλη Lorenz",
            labels={'x': 'Σωρευτικό % Μουσείων', 'y': 'Σωρευτικό % Επισκεπτών'}
        )
        fig_l.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                        line=dict(dash="dash", color="red"))
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.info("Ο δείκτης Gini υπολογίζεται μόνο για πολλαπλά μουσεία.")

st.divider()

# ═════════════════════════════════════════════
# 10. ΕΠΙΣΚΕΨΙΜΟΤΗΤΑ ΑΝΑ ΠΕΡΙΦΕΡΕΙΑ
# ═════════════════════════════════════════════
if selected_museum == "Όλα":
    st.subheader("🌍 Επισκεψιμότητα ανά Περιφέρεια")
    reg_data = (
        final_df.groupby('Region')['Visitors']
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    # Κανονικοποιημένη (αν υπάρχει πληροφορία για # μουσείων)
    reg_museum_count = final_df.groupby('Region')['Museum'].nunique().reset_index()
    reg_museum_count.columns = ['Region', 'Museum_Count']
    reg_data = reg_data.merge(reg_museum_count, on='Region')
    reg_data['Επισκέπτες/Μουσείο'] = (reg_data['Visitors'] / reg_data['Museum_Count']).round(0)

    reg_data['Ποσοστό (%)'] = (
        reg_data['Visitors'] / reg_data['Visitors'].sum() * 100
    ).round(2)

    tab_abs, tab_norm, tab_pct = st.tabs([
        "Απόλυτα", "Ανά Μουσείο", "Ποσοστά %"
    ])

    with tab_abs:
        fig_reg = px.bar(
            reg_data, x='Visitors', y='Region', orientation='h',
            title="Κατάταξη Περιφερειών (Συνολικοί Επισκέπτες)",
            color='Visitors', color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_reg, use_container_width=True)

    with tab_norm:
        fig_reg_n = px.bar(
            reg_data.sort_values('Επισκέπτες/Μουσείο'),
            x='Επισκέπτες/Μουσείο', y='Region', orientation='h',
            title="Κατάταξη Περιφερειών (Επισκέπτες ανά Μουσείο)",
            color='Επισκέπτες/Μουσείο', color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_reg_n, use_container_width=True)

    with tab_pct:
        fig_pct = px.bar(
            reg_data.sort_values('Ποσοστό (%)'),
            x='Ποσοστό (%)', y='Region', orientation='h',
            title="Μερίδιο Επισκεψιμότητας ανά Περιφέρεια (%)",
            color='Ποσοστό (%)', color_continuous_scale='Blues',
            text='Ποσοστό (%)'
        )
        fig_pct.update_traces(
            texttemplate='%{text:.2f}%',
            textposition='outside'
        )
        st.plotly_chart(fig_pct, use_container_width=True)

        st.dataframe(
            reg_data[['Region', 'Visitors', 'Ποσοστό (%)']]
            .sort_values('Ποσοστό (%)', ascending=False)
            .reset_index(drop=True)
            .style.format({'Visitors': '{:,.0f}', 'Ποσοστό (%)': '{:.2f}%'}),
            use_container_width=True
        )

st.divider()

# ═════════════════════════════════════════════
# 11. ΕΠΙΣΚΕΨΙΜΟΤΗΤΑ ΑΝΑ ΠΕΡΙΦΕΡΕΙΑ & ΕΠΟΧΗ
# ═════════════════════════════════════════════
if selected_museum == "Όλα":
    st.subheader("🌸 Επισκεψιμότητα ανά Περιφέρεια & Εποχή")

    SEASONS = {
        "🌸 Άνοιξη":    [3, 4, 5],
        "☀️ Καλοκαίρι": [6, 7, 8],
        "🍂 Φθινόπωρο": [9, 10, 11],
        "❄️ Χειμώνας":  [12, 1, 2],
    }

    season_tabs = st.tabs(list(SEASONS.keys()))

    for tab, (season_name, months) in zip(season_tabs, SEASONS.items()):
        with tab:
            season_df = (
                final_df[final_df['Month'].isin(months)]
                .groupby('Region')['Visitors']
                .sum()
                .reset_index()
            )
            season_df['Ποσοστό (%)'] = (
                season_df['Visitors'] / season_df['Visitors'].sum() * 100
            ).round(2)
            season_df = season_df.sort_values('Visitors', ascending=True)

            fig_season = px.bar(
                season_df,
                x='Visitors', y='Region', orientation='h',
                title=f"Επισκεψιμότητα ανά Περιφέρεια — {season_name}",
                color='Visitors', color_continuous_scale='Blues',
                text='Ποσοστό (%)'
            )
            fig_season.update_traces(
                texttemplate='%{text:.2f}%',
                textposition='outside'
            )
            st.plotly_chart(fig_season, use_container_width=True)

            st.dataframe(
                season_df[['Region', 'Visitors', 'Ποσοστό (%)']]
                .sort_values('Ποσοστό (%)', ascending=False)
                .reset_index(drop=True)
                .style.format({'Visitors': '{:,.0f}', 'Ποσοστό (%)': '{:.2f}%'}),
                use_container_width=True
            )

st.divider()

# ═════════════════════════════════════════════
# 12. GOOGLE RATINGS ΑΝΑΛΥΣΗ
# ═════════════════════════════════════════════
if not df_places.empty:
    st.subheader("⭐ Ανάλυση Google Ratings")

    # Συγχώνευση με επισκεψιμότητα
    visitors_total = (
        final_df.groupby('Museum')['Visitors'].sum().reset_index()
    )
    df_merged = df_places.merge(visitors_total, on='Museum', how='inner')
    df_merged = df_merged[df_merged['Rating'].notna()].copy()

    tab_r1, tab_r2, tab_r3 = st.tabs([
        "🏅 Top/Bottom Ratings",
        "📊 Rating vs Επισκεψιμότητα",
        "📋 Πλήρης Πίνακας"
    ])

    with tab_r1:
        col_t, col_b = st.columns(2)
        with col_t:
            st.write("🔝 Top 10 — Υψηλότερη Βαθμολογία")
            top_r = (df_merged[['Museum', 'Rating', 'Ratings_Total', 'Google_Maps_URL']]
                     .sort_values('Rating', ascending=False).head(10).reset_index(drop=True))
            st.dataframe(
                top_r.style.format({'Rating': '{:.1f}', 'Ratings_Total': '{:,.0f}'}),
                use_container_width=True
            )
        with col_b:
            st.write("🔻 Bottom 10 — Χαμηλότερη Βαθμολογία")
            bot_r = (df_merged[['Museum', 'Rating', 'Ratings_Total', 'Google_Maps_URL']]
                     .sort_values('Rating').head(10).reset_index(drop=True))
            st.dataframe(
                bot_r.style.format({'Rating': '{:.1f}', 'Ratings_Total': '{:,.0f}'}),
                use_container_width=True
            )

        # Κατανομή ratings
        fig_hist = px.histogram(
            df_merged, x='Rating', nbins=20,
            title="Κατανομή Google Ratings",
            labels={'Rating': 'Βαθμολογία', 'count': 'Αριθμός Μουσείων'},
            color_discrete_sequence=['#4A90D9']
        )
        fig_hist.add_vline(
            x=df_merged['Rating'].mean(), line_dash="dash", line_color="red",
            annotation_text=f"Μέσος: {df_merged['Rating'].mean():.2f}"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab_r2:
        if 'Visitors' in df_merged.columns:
            fig_scatter = px.scatter(
                df_merged,
                x='Visitors', y='Rating',
                size='Ratings_Total',
                hover_name='Museum',
                title="Google Rating vs Επισκεψιμότητα",
                labels={
                    'Visitors': 'Συνολικοί Επισκέπτες',
                    'Rating': 'Google Rating',
                    'Ratings_Total': 'Αριθμός Κριτικών'
                },
                color='Rating',
                color_continuous_scale='RdYlGn',
                log_x=True
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption("💡 Μέγεθος bubble = αριθμός κριτικών | Χρώμα = βαθμολογία | Άξονας Χ σε λογαριθμική κλίμακα")

    with tab_r3:
        df_table = df_merged[['Museum', 'Region', 'Rating', 'Ratings_Total', 'Address', 'Google_Maps_URL']].copy()
        df_table = df_table.sort_values('Rating', ascending=False).reset_index(drop=True)
        df_table['Google_Maps_URL'] = df_table['Google_Maps_URL'].apply(
            lambda x: f'[🗺️ Maps]({x})' if pd.notna(x) and x != '' else '—'
        )
        st.dataframe(
            df_table.style.format({
                'Rating': '{:.1f}',
                'Ratings_Total': '{:,.0f}'
            }),
            use_container_width=True
        )

        excel_ratings = to_excel(
            df_merged[['Museum','Region','Rating','Ratings_Total','Address','Google_Maps_URL']]
            .sort_values('Rating', ascending=False)
        )
        st.download_button(
            "📊 Λήψη Ratings (.xlsx)",
            data=excel_ratings,
            file_name='museums_ratings.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

st.divider()

# ═════════════════════════════════════════════
# 13. VISITORS vs MONTH / REGION / SENTIMENT
# ═════════════════════════════════════════════
st.subheader("📊 Συγκριτικές Αναλύσεις")

tab_vm, tab_vr, tab_vs = st.tabs([
    "📅 Visitors vs Month",
    "🌍 Visitors vs Region",
    "💬 Visitors vs Sentiment"
])

# ── Visitors vs Month ─────────────────────────
with tab_vm:
    monthly_vis = (
        final_df.groupby('Month')['Visitors']
        .agg(['sum', 'mean', 'median'])
        .reset_index()
    )
    monthly_vis.columns = ['Month', 'Σύνολο', 'Μέσος Όρος', 'Διάμεσος']
    monthly_vis['Μήνας'] = monthly_vis['Month'].map(MONTH_NAMES)

    metric_choice = st.radio(
        "Μετρική:", ["Σύνολο", "Μέσος Όρος", "Διάμεσος"],
        horizontal=True, key="vm_metric"
    )

    fig_vm = px.bar(
        monthly_vis, x='Μήνας', y=metric_choice,
        title=f"Επισκέπτες ανά Μήνα — {metric_choice}",
        color=metric_choice, color_continuous_scale='Blues',
        text=metric_choice,
        category_orders={'Μήνας': list(MONTH_NAMES.values())}
    )
    fig_vm.update_traces(
        texttemplate='%{text:,.0f}', textposition='outside'
    )
    fig_vm.add_hline(
        y=monthly_vis[metric_choice].mean(),
        line_dash="dash", line_color="red",
        annotation_text="Μέσος Όρος"
    )
    st.plotly_chart(fig_vm, use_container_width=True)

    # Box plot εποχικότητας
    final_df_month = final_df.copy()
    final_df_month['Μήνας'] = final_df_month['Month'].map(MONTH_NAMES)
    fig_box = px.box(
        final_df_month,
        x='Μήνας', y='Visitors',
        title="Κατανομή Επισκεπτών ανά Μήνα (Box Plot)",
        color='Μήνας',
        category_orders={'Μήνας': list(MONTH_NAMES.values())}
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# ── Visitors vs Region ────────────────────────
with tab_vr:
    reg_vis = (
        final_df.groupby('Region')['Visitors']
        .agg(['sum', 'mean'])
        .reset_index()
    )
    reg_vis.columns = ['Region', 'Σύνολο', 'Μέσος/Μήνα']

    col_rv1, col_rv2 = st.columns(2)

    with col_rv1:
        fig_vr1 = px.bar(
            reg_vis.sort_values('Σύνολο'),
            x='Σύνολο', y='Region', orientation='h',
            title="Συνολικοί Επισκέπτες ανά Περιφέρεια",
            color='Σύνολο', color_continuous_scale='Blues',
            text='Σύνολο'
        )
        fig_vr1.update_traces(
            texttemplate='%{text:,.0f}', textposition='outside'
        )
        st.plotly_chart(fig_vr1, use_container_width=True)

    with col_rv2:
        fig_vr2 = px.bar(
            reg_vis.sort_values('Μέσος/Μήνα'),
            x='Μέσος/Μήνα', y='Region', orientation='h',
            title="Μέσος Μηνιαίος Επισκέπτης ανά Περιφέρεια",
            color='Μέσος/Μήνα', color_continuous_scale='Greens',
            text='Μέσος/Μήνα'
        )
        fig_vr2.update_traces(
            texttemplate='%{text:,.0f}', textposition='outside'
        )
        st.plotly_chart(fig_vr2, use_container_width=True)

    # Treemap
    fig_tree = px.treemap(
        reg_vis,
        path=['Region'],
        values='Σύνολο',
        title="Treemap Επισκεψιμότητας ανά Περιφέρεια",
        color='Σύνολο', color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_tree, use_container_width=True)

# ── Visitors vs Sentiment (Google Rating) ─────
with tab_vs:
    if not df_places.empty:
        visitors_total = (
            final_df.groupby('Museum')['Visitors'].sum().reset_index()
        )
        df_sent = df_places.merge(visitors_total, on='Museum', how='inner')
        df_sent = df_sent[df_sent['Rating'].notna() & df_sent['Visitors'].notna()].copy()

        # Κατηγοριοποίηση sentiment
        def sentiment_label(r):
            if r >= 4.5:   return '🟢 Πολύ Θετικό (≥4.5)'
            elif r >= 4.0: return '🔵 Θετικό (4.0–4.4)'
            elif r >= 3.5: return '🟡 Μέτριο (3.5–3.9)'
            else:          return '🔴 Αρνητικό (<3.5)'

        df_sent['Sentiment'] = df_sent['Rating'].apply(sentiment_label)

        sent_order = [
            '🟢 Πολύ Θετικό (≥4.5)',
            '🔵 Θετικό (4.0–4.4)',
            '🟡 Μέτριο (3.5–3.9)',
            '🔴 Αρνητικό (<3.5)'
        ]

        # KPIs ανά sentiment
        sent_summary = (
            df_sent.groupby('Sentiment')
            .agg(Μουσεία=('Museum', 'count'), Επισκέπτες=('Visitors', 'sum'))
            .reindex([s for s in sent_order if s in df_sent['Sentiment'].unique()])
            .reset_index()
        )

        s_cols = st.columns(len(sent_summary))
        for col, (_, row) in zip(s_cols, sent_summary.iterrows()):
            col.metric(
                row['Sentiment'],
                f"{int(row['Επισκέπτες']):,}",
                f"{int(row['Μουσεία'])} μουσεία"
            )

        st.markdown("---")

        # Scatter: Rating vs Visitors
        fig_sent1 = px.scatter(
            df_sent,
            x='Rating', y='Visitors',
            color='Sentiment',
            size='Ratings_Total',
            hover_name='Museum',
            title="Google Rating vs Επισκεψιμότητα ανά Μουσείο",
            labels={
                'Rating': 'Google Rating',
                'Visitors': 'Συνολικοί Επισκέπτες',
                'Ratings_Total': 'Αριθμός Κριτικών'
            },
            category_orders={'Sentiment': sent_order},
            color_discrete_map={
                '🟢 Πολύ Θετικό (≥4.5)': '#2ecc71',
                '🔵 Θετικό (4.0–4.4)':   '#3498db',
                '🟡 Μέτριο (3.5–3.9)':   '#f1c40f',
                '🔴 Αρνητικό (<3.5)':    '#e74c3c'
            },
            log_y=True
        )
        st.plotly_chart(fig_sent1, use_container_width=True)

        # Box plot επισκεπτών ανά sentiment
        fig_sent2 = px.box(
            df_sent,
            x='Sentiment', y='Visitors',
            color='Sentiment',
            title="Κατανομή Επισκεπτών ανά Κατηγορία Sentiment",
            labels={'Visitors': 'Συνολικοί Επισκέπτες'},
            category_orders={'Sentiment': sent_order},
            color_discrete_map={
                '🟢 Πολύ Θετικό (≥4.5)': '#2ecc71',
                '🔵 Θετικό (4.0–4.4)':   '#3498db',
                '🟡 Μέτριο (3.5–3.9)':   '#f1c40f',
                '🔴 Αρνητικό (<3.5)':    '#e74c3c'
            },
            log_y=True
        )
        fig_sent2.update_layout(showlegend=False)
        st.plotly_chart(fig_sent2, use_container_width=True)
        st.caption("💡 Άξονας Y σε λογαριθμική κλίμακα λόγω μεγάλης απόκλισης τιμών")
    else:
        st.info("Απαιτείται το αρχείο museums_place_ids.csv για την ανάλυση Sentiment.")

st.divider()

# ═════════════════════════════════════════════
# 14. ΑΝΑΛΥΤΙΚΟΣ ΠΙΝΑΚΑΣ & DOWNLOAD
# ═════════════════════════════════════════════
st.subheader("📋 Αναλυτικά Στοιχεία (Πίνακας)")
st.dataframe(
    final_df[['Region', 'Museum', 'Year', 'Month', 'Visitors']],
    use_container_width=True
)

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        "📥 Λήψη CSV (UTF-8)",
        data=csv,
        file_name='museum_stats.csv',
        mime='text/csv'
    )

with col_dl2:
    excel_data = to_excel(final_df[['Region', 'Museum', 'Year', 'Month', 'Visitors']])
    st.download_button(
        "📊 Λήψη Excel (.xlsx)",
        data=excel_data,
        file_name='museum_stats.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
