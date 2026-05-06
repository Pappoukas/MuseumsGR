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
        df_p = pd.read_csv('museums_place_ids.csv', encoding='utf-8-sig')
        df_p = df_p[[
            'Museum', 'Region', 'Regional_Unit', 'Place_ID',
            'Google_Maps_URL', 'Rating', 'Ratings_Total', 'Address',
            'Lat', 'Lng'          # ← νέες στήλες
        ]].copy()
        df_p['Rating']        = pd.to_numeric(df_p['Rating'],        errors='coerce')
        df_p['Ratings_Total'] = pd.to_numeric(df_p['Ratings_Total'], errors='coerce')
        df_p['Lat']           = pd.to_numeric(df_p['Lat'],           errors='coerce')
        df_p['Lng']           = pd.to_numeric(df_p['Lng'],           errors='coerce')
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
# 14. ΣΥΓΚΡΙΣΗ ΜΟΥΣΕΙΩΝ
# ═════════════════════════════════════════════
st.subheader("🆚 Σύγκριση Μουσείων")

all_museums = sorted(final_df['Museum'].dropna().unique())

cmp_col1, cmp_col2 = st.columns(2)
with cmp_col1:
    museum_a = st.selectbox("🔵 Μουσείο Α", all_museums,
                             index=0, key="cmp_a")
with cmp_col2:
    museum_b = st.selectbox("🔴 Μουσείο Β", all_museums,
                             index=min(1, len(all_museums)-1), key="cmp_b")

if museum_a == museum_b:
    st.warning("Επίλεξε δύο διαφορετικά μουσεία για σύγκριση.")
else:
    df_a = final_df[final_df['Museum'] == museum_a]
    df_b = final_df[final_df['Museum'] == museum_b]

    # ── KPI Cards ──────────────────────────────
    st.markdown("#### 📊 Βασικά Στατιστικά")

    def museum_kpis(df, places_df, name):
        total    = df['Visitors'].sum()
        avg      = df['Visitors'].mean()
        med      = df['Visitors'].median()
        best_y   = df.groupby('Year')['Visitors'].sum().idxmax() if not df.empty else '—'
        peak_m   = MONTH_NAMES.get(int(df.groupby('Month')['Visitors'].mean().idxmax()), '—') if not df.empty else '—'
        rating   = '—'
        reviews  = '—'
        maps_url = ''
        if not places_df.empty:
            row = places_df[places_df['Museum'] == name]
            if not row.empty:
                r = row.iloc[0]
                rating   = f"{r['Rating']:.1f} ⭐" if pd.notna(r['Rating']) else '—'
                reviews  = f"{int(r['Ratings_Total']):,}" if pd.notna(r['Ratings_Total']) else '—'
                maps_url = r['Google_Maps_URL'] if pd.notna(r['Google_Maps_URL']) else ''
        return {
            'Σύνολο Επισκεπτών': f"{total:,.0f}",
            'Μέσος / Μήνα':      f"{avg:,.0f}",
            'Διάμεσος / Μήνα':   f"{med:,.0f}",
            'Καλύτερο Έτος':     str(best_y),
            'Peak Μήνας':        peak_m,
            'Google Rating':     rating,
            'Κριτικές Google':   reviews,
            'Google Maps':       maps_url,
        }

    kpi_a = museum_kpis(df_a, df_places, museum_a)
    kpi_b = museum_kpis(df_b, df_places, museum_b)

    kpi_keys = [k for k in kpi_a if k != 'Google Maps']
    hdr, col_a, col_b = st.columns([2, 1, 1])
    hdr.markdown("**Δείκτης**")
    col_a.markdown(f"**🔵 {museum_a}**")
    col_b.markdown(f"**🔴 {museum_b}**")

    for k in kpi_keys:
        hdr, col_a, col_b = st.columns([2, 1, 1])
        hdr.write(k)
        col_a.write(kpi_a[k])
        col_b.write(kpi_b[k])

    if kpi_a['Google Maps']:
        st.markdown(f"🔵 [Google Maps — {museum_a}]({kpi_a['Google Maps']})")
    if kpi_b['Google Maps']:
        st.markdown(f"🔴 [Google Maps — {museum_b}]({kpi_b['Google Maps']})")

    st.markdown("---")

    # ── Tabs με γραφήματα ──────────────────────
    tab_c1, tab_c2, tab_c3, tab_c4 = st.tabs([
        "📈 Χρονοσειρά",
        "📅 Μηνιαία Σύγκριση",
        "📆 Ετήσια Σύγκριση",
        "🔥 Heatmap"
    ])

    # Χρονοσειρά
    with tab_c1:
        ts_a = df_a.groupby('Date')['Visitors'].sum().reset_index()
        ts_b = df_b.groupby('Date')['Visitors'].sum().reset_index()
        ts_a['Μουσείο'] = museum_a
        ts_b['Μουσείο'] = museum_b
        ts_all = pd.concat([ts_a, ts_b])

        fig_ts = px.line(
            ts_all, x='Date', y='Visitors', color='Μουσείο',
            line_shape='spline',
            title="Μηνιαία Χρονοσειρά Επισκεψιμότητας",
            color_discrete_map={museum_a: '#3498db', museum_b: '#e74c3c'}
        )
        fig_ts.add_vrect(
            x0="2020-03-01", x1="2021-06-01",
            fillcolor="gray", opacity=0.08,
            annotation_text="COVID-19", annotation_position="top left"
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    # Μηνιαία
    with tab_c2:
        ma_a = df_a.groupby('Month')['Visitors'].mean().reset_index()
        ma_b = df_b.groupby('Month')['Visitors'].mean().reset_index()
        ma_a['Μουσείο'] = museum_a
        ma_b['Μουσείο'] = museum_b
        ma_all = pd.concat([ma_a, ma_b])
        ma_all['Μήνας'] = ma_all['Month'].map(MONTH_NAMES)

        fig_ma = px.bar(
            ma_all, x='Μήνας', y='Visitors', color='Μουσείο',
            barmode='group',
            title="Μέσος Μηνιαίος Επισκέπτης ανά Μήνα",
            color_discrete_map={museum_a: '#3498db', museum_b: '#e74c3c'},
            category_orders={'Μήνας': list(MONTH_NAMES.values())}
        )
        st.plotly_chart(fig_ma, use_container_width=True)

    # Ετήσια
    with tab_c3:
        ya_a = df_a.groupby('Year')['Visitors'].sum().reset_index()
        ya_b = df_b.groupby('Year')['Visitors'].sum().reset_index()
        ya_a['Μουσείο'] = museum_a
        ya_b['Μουσείο'] = museum_b
        ya_all = pd.concat([ya_a, ya_b])

        fig_ya = px.bar(
            ya_all, x='Year', y='Visitors', color='Μουσείο',
            barmode='group',
            title="Ετήσια Επισκεψιμότητα",
            color_discrete_map={museum_a: '#3498db', museum_b: '#e74c3c'}
        )
        st.plotly_chart(fig_ya, use_container_width=True)

        # Ποσοστιαία μεταβολή
        ya_pivot = ya_all.pivot(index='Year', columns='Μουσείο', values='Visitors')
        ya_pivot[f'Μεταβολή {museum_a} (%)'] = ya_pivot[museum_a].pct_change() * 100
        ya_pivot[f'Μεταβολή {museum_b} (%)'] = ya_pivot[museum_b].pct_change() * 100
        st.dataframe(
            ya_pivot.style.format({
                museum_a: '{:,.0f}', museum_b: '{:,.0f}',
                f'Μεταβολή {museum_a} (%)': '{:+.1f}%',
                f'Μεταβολή {museum_b} (%)': '{:+.1f}%',
            }),
            use_container_width=True
        )

    # Heatmap
    with tab_c4:
        def make_heatmap(df, name, color):
            hm = (
                df.groupby(['Year', 'Month'])['Visitors']
                .sum().reset_index()
                .pivot(index='Year', columns='Month', values='Visitors')
            )
            hm.columns = [MONTH_NAMES.get(c, c) for c in hm.columns]
            fig = px.imshow(
                hm, color_continuous_scale=color, aspect='auto',
                title=f"Heatmap — {name}",
                labels=dict(x="Μήνας", y="Έτος", color="Επισκέπτες")
            )
            return fig

        hm_col1, hm_col2 = st.columns(2)
        with hm_col1:
            st.plotly_chart(
                make_heatmap(df_a, museum_a, 'Blues'),
                use_container_width=True
            )
        with hm_col2:
            st.plotly_chart(
                make_heatmap(df_b, museum_b, 'Reds'),
                use_container_width=True
            )

st.divider()

# ═════════════════════════════════════════════
# 15. ΑΝΑΛΥΤΙΚΟΣ ΠΙΝΑΚΑΣ & DOWNLOAD
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

# ═══════════════════════════════════════════════════════════════
# 16. ΓΕΩΓΡΑΦΙΚΗ ΚΑΤΑΝΟΜΗ ΜΟΥΣΕΙΩΝ
# ═══════════════════════════════════════════════════════════════

st.divider()
st.subheader("🗺️ Γεωγραφική Κατανομή Μουσείων")

import json, os

# ── Mapping: Regional_Unit (γενική) → name_greek στο GeoJSON (ονομαστική) ──
RU_TO_GEOJSON = {
    "Αιτωλοακαρνανίας": "Αιτωλοακαρνανία",
    "Αργολίδας":        "Αργολίδα",
    "Αρκαδίας":         "Αρκαδία",
    "Αττικής":          "Αθήνα",           # Αττική → κεντρικός πυρήνας
    "Αχαΐας":           "Αχαΐα",
    "Βοιωτίας":         "Βοιωτία",
    "Γρεβενών":         "Γρεβενά",
    "Δράμας":           "Δράμα",
    "Δωδεκανήσου":      "Δωδεκάνησα",
    "Εύβοιας":          "Εύβοια",
    "Ευρυτανίας":       "Ευρυτανία",
    "Ζακύνθου":         "Ζάκυνθος",
    "Ηλείας":           "Ηλεία",
    "Ημαθίας":          "Ημαθία",
    "Ηρακλείου":        "Ηράκλειο",
    "Θεσπρωτίας":       "Θεσπρωτία",
    "Θεσσαλονίκης":     "Θεσσαλονίκη",
    "Ιωαννίνων":        "Ιωάννινα",
    "Κέρκυρας":         "Κέρκυρα",
    "Καβάλας":          "Καβάλα",
    "Καρδίτσας":        "Καρδίτσα",
    "Καστοριάς":        "Καστοριά",
    "Κεφαλληνίας":      "Κεφαλλονία",
    "Κιλκίς":           "Κιλκίς",
    "Κοζάνης":          "Κοζάνη",
    "Κορινθίας":        "Κόρινθος",
    "Κυκλάδων":         "Κυκλάδες",
    "Λάρισας":          "Λάρισα",
    "Λέσβου":           "Λέσβος",
    "Λακωνίας":         "Λακωνία",
    "Λασιθίου":         "Λασίθιο",
    "Λευκάδας":         "Λευκάδα",
    "Μαγνησίας":        "Μαγνησία",
    "Μεσσηνίας":        "Μεσσηνία",
    "Ξάνθης":           "Ξάνθη",
    "Πέλλας":           "Πέλλα",
    "Πιερίας":          "Πιερία",
    "Πρέβεζας":         "Πρέβεζα",
    "Ρεθύμνου":         "Ρέθυμνο",
    "Ροδόπης":          "Ροδόπη",
    "Σάμου":            "Σάμος",
    "Σερρών":           "Σέρρες",
    "Φθιώτιδας":        "Φθιώτιδα",
    "Φλώρινας":         "Φλώρινα",
    "Φωκίδας":          "Φωκίδα",
    "Χίου":             "Χίος",
    "Χαλκιδικής":       "Χαλκιδική",
    "Χανίων":           "Χανιά",
    "Άρτας":            "Άρτα",
    "Έβρου":            "Έβρος",
}

@st.cache_data
def load_geojson():
    if os.path.exists("greece_regions.geojson"):
        with open("greece_regions.geojson", encoding="utf-8") as f:
            return json.load(f)
    return None

@st.cache_data
def load_places_map():
    if not os.path.exists("museums_place_ids.csv"):
        return pd.DataFrame()
    df_m = pd.read_csv("museums_place_ids.csv", encoding="utf-8-sig")
    df_m["Rating"]        = pd.to_numeric(df_m.get("Rating"),        errors="coerce")
    df_m["Ratings_Total"] = pd.to_numeric(df_m.get("Ratings_Total"), errors="coerce")
    for col in ("Lat", "Lng"):
        if col in df_m.columns:
            df_m[col] = pd.to_numeric(df_m[col], errors="coerce")
    return df_m

geojson_data = load_geojson()
df_map       = load_places_map()

if geojson_data is None:
    st.warning("Δεν βρέθηκε το αρχείο greece_regions.geojson.")
else:
    # ── Υπολογισμός επισκεψιμότητας ανά Περιφερειακή Ενότητα ──────────────────
    visitors_by_ru = (
        final_df.groupby("Regional_Unit")["Visitors"]
        .sum()
        .reset_index()
        .rename(columns={"Visitors": "Total_Visitors"})
    )
    visitors_by_ru["GeoName"] = visitors_by_ru["Regional_Unit"].map(RU_TO_GEOJSON)

    # Αριθμός μουσείων ανά ΠΕ
    museum_count = (
        final_df.groupby("Regional_Unit")["Museum"]
        .nunique()
        .reset_index()
        .rename(columns={"Museum": "Museum_Count"})
    )
    visitors_by_ru = visitors_by_ru.merge(museum_count, on="Regional_Unit", how="left")

    # ── Tabs χάρτη ─────────────────────────────────────────────────────────────
    has_coords = (
        not df_map.empty
        and "Lat" in df_map.columns
        and df_map["Lat"].notna().sum() > 10
    )

    map_tabs = st.tabs(["🌡️ Χάρτης Επισκεψιμότητας (Χωροπλήθης)", "📍 Διασπορά Μουσείων"])

    # ══ TAB 1: ΧΩΡΟΠΛΗΘΗΣ ΧΑΡΤΗΣ ════════════════════════════════════════════
    with map_tabs[0]:
        st.caption(
            "Κάθε Περιφερειακή Ενότητα χρωματίζεται ανάλογα με τον "
            "συνολικό αριθμό επισκεπτών στην επιλεγμένη περίοδο."
        )

        # Για τον χωροπλήθη χρειαζόμαστε το id να ταιριάζει με το featureidkey
        geo_df = visitors_by_ru.dropna(subset=["GeoName"]).copy()

        fig_choro = px.choropleth_mapbox(
            geo_df,
            geojson=geojson_data,
            locations="GeoName",
            featureidkey="properties.name_greek",
            color="Total_Visitors",
            hover_name="Regional_Unit",
            hover_data={
                "GeoName":       False,
                "Total_Visitors": ":,.0f",
                "Museum_Count":  True,
            },
            labels={
                "Total_Visitors": "Επισκέπτες",
                "Museum_Count":   "Μουσεία",
            },
            color_continuous_scale="YlOrRd",
            mapbox_style="carto-positron",
            zoom=5.2,
            center={"lat": 39.0, "lon": 22.5},
            opacity=0.75,
            title="Συνολική Επισκεψιμότητα ανά Περιφερειακή Ενότητα",
        )
        fig_choro.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="Επισκέπτες"),
        )
        st.plotly_chart(fig_choro, use_container_width=True)

        # Πίνακας στατιστικών ανά ΠΕ
        with st.expander("📋 Αναλυτικός Πίνακας ανά Περιφερειακή Ενότητα"):
            tbl = (
                geo_df[["Regional_Unit", "Museum_Count", "Total_Visitors"]]
                .sort_values("Total_Visitors", ascending=False)
                .reset_index(drop=True)
            )
            tbl.index += 1
            st.dataframe(
                tbl.style.format({
                    "Total_Visitors": "{:,.0f}",
                    "Museum_Count":   "{:,.0f}",
                }),
                use_container_width=True,
            )

    # ══ TAB 2: SCATTER ΧΑΡΤΗΣ ΜΟΥΣΕΙΩΝ ══════════════════════════════════════
    with map_tabs[1]:
        if not has_coords:
            st.info(
                "⚠️ Δεν βρέθηκαν συντεταγμένες στο museums_place_ids.csv.\n\n"
                "Εκτέλεσε τοπικά το **geocode_museums.py** για να τις προσθέσεις "
                "αυτόματα, και ανέβασε το ενημερωμένο CSV στο repository."
            )
        else:
            # Συγχώνευση με επισκεψιμότητα
            vis_total = (
                final_df.groupby("Museum")["Visitors"].sum().reset_index()
                .rename(columns={"Visitors": "Total_Visitors"})
            )
            df_scatter = df_map.merge(vis_total, on="Museum", how="left")
            df_scatter  = df_scatter.dropna(subset=["Lat", "Lng"]).copy()
            df_scatter["Total_Visitors"] = df_scatter["Total_Visitors"].fillna(0)
            df_scatter["Rating"]         = df_scatter["Rating"].fillna(0)

            # Επιλογή χρωματισμού
            color_by = st.radio(
                "Χρωματισμός σημείων:",
                ["Google Rating", "Επισκεψιμότητα"],
                horizontal=True,
            )

            if color_by == "Google Rating":
                color_col   = "Rating"
                color_label = "⭐ Rating"
                color_scale = "RdYlGn"
                hover_extra = {"Rating": ":.1f", "Total_Visitors": ":,.0f"}
            else:
                color_col   = "Total_Visitors"
                color_label = "Επισκέπτες"
                color_scale = "YlOrRd"
                hover_extra = {"Rating": ":.1f", "Total_Visitors": ":,.0f"}

            fig_scatter = px.scatter_mapbox(
                df_scatter,
                lat="Lat",
                lon="Lng",
                size="Total_Visitors",
                size_max=35,
                color=color_col,
                color_continuous_scale=color_scale,
                hover_name="Museum",
                hover_data={
                    "Lat":   False,
                    "Lng":   False,
                    **hover_extra,
                    "Regional_Unit": True,
                    "Address":       True,
                },
                labels={
                    "Total_Visitors": "Επισκέπτες",
                    "Rating":         "⭐ Rating",
                    "Regional_Unit":  "Περιφερειακή Ενότητα",
                    "Address":        "Διεύθυνση",
                },
                mapbox_style="carto-positron",
                zoom=5.2,
                center={"lat": 39.0, "lon": 22.5},
                title=f"Διασπορά Μουσείων — χρωματισμός: {color_by}",
            )
            fig_scatter.update_layout(
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
                coloraxis_colorbar=dict(title=color_label),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Σύνοψη
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Μουσεία στον χάρτη", f"{len(df_scatter):,}")
            col_m2.metric(
                "Χωρίς συντεταγμένες",
                f"{df_map['Lat'].isna().sum():,}",
            )
            top_museum = df_scatter.loc[df_scatter["Total_Visitors"].idxmax(), "Museum"] if len(df_scatter) > 0 else "—"
            col_m3.metric("Πρώτο σε επισκέπτες", top_museum[:30])

st.divider()

st.divider()

# ═══════════════════════════════════════════════════════════════
# 18. CLUSTERING ΜΟΥΣΕΙΩΝ
# ═══════════════════════════════════════════════════════════════
st.subheader("🔵 Clustering Μουσείων")
st.markdown(
    "Ανακαλύψτε ομάδες μουσείων με παρόμοια χαρακτηριστικά — "
    "γεωγραφική εγγύτητα ή κοινό προφίλ επισκεψιμότητας."
)

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    sklearn_ok = True
except ImportError:
    sklearn_ok = False
    st.warning("Απαιτείται `scikit-learn`. Πρόσθεσέ το στο `requirements.txt`.")

if sklearn_ok and not df_places.empty:

    # ── Προετοιμασία δεδομένων ────────────────────────────────────────────────
    @st.cache_data
    def build_cluster_df(_df_places_hash):
        dp = df_places.copy()
        dp["Lat"] = pd.to_numeric(dp["Lat"], errors="coerce")
        dp["Lng"] = pd.to_numeric(dp["Lng"], errors="coerce")
        dp["Rating"] = pd.to_numeric(dp["Rating"], errors="coerce")

        # Εποχική κατανομή
        monthly_raw = (
            df.groupby(["Museum", "Month"])["Visitors"]
            .sum().reset_index()
        )
        seasonal = (
            monthly_raw
            .pivot(index="Museum", columns="Month", values="Visitors")
            .fillna(0)
        )
        seasonal_norm = seasonal.div(
            seasonal.sum(axis=1).replace(0, np.nan), axis=0
        ).fillna(0)
        seasonal_norm.columns = [f"m{c}" for c in seasonal_norm.columns]

        # Στατιστικά επισκεψιμότητας
        vis = (
            df.groupby("Museum")["Visitors"]
            .agg(Total_Visitors="sum", Mean_Monthly="mean", Std_Monthly="std")
            .reset_index()
        )
        vis["CV"] = (
            vis["Std_Monthly"] / vis["Mean_Monthly"].replace(0, np.nan)
        ).fillna(0)
        vis["Log_Visitors"] = np.log1p(vis["Total_Visitors"])

        merged = dp.merge(vis, on="Museum", how="inner")
        merged = merged.merge(seasonal_norm.reset_index(), on="Museum", how="inner")
        merged = merged.dropna(subset=["Lat", "Lng"])

        merged["Summer_Pct"] = merged[["m6","m7","m8"]].sum(axis=1)
        merged["Winter_Pct"] = merged[["m12","m1","m2"]].sum(axis=1)
        merged["Spring_Pct"] = merged[["m3","m4","m5"]].sum(axis=1)
        merged["Autumn_Pct"] = merged[["m9","m10","m11"]].sum(axis=1)

        return merged

    df_cl = build_cluster_df(len(df_places))

    tab_geo, tab_beh, tab_combo = st.tabs([
        "🗺️ Γεωγραφικό Clustering",
        "📊 Behavioral Clustering",
        "🔀 Συνδυαστικός Χάρτης",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — ΓΕΩΓΡΑΦΙΚΟ CLUSTERING
    # ════════════════════════════════════════════════════════════════════
    with tab_geo:
        st.markdown(
            "Ομαδοποίηση με βάση τις **γεωγραφικές συντεταγμένες** (KMeans). "
            "Αποκαλύπτει φυσικές ζώνες συγκέντρωσης μουσείων."
        )

        k_geo = st.slider(
            "Αριθμός γεωγραφικών ομάδων (k):",
            min_value=3, max_value=8, value=6, key="k_geo",
        )

        geo_feats = df_cl[["Lat","Lng"]].values
        km_geo = KMeans(n_clusters=k_geo, random_state=42, n_init=10)
        df_cl["Geo_Cluster"] = km_geo.fit_predict(geo_feats).astype(str)

        GEO_COLORS = [
            "#e74c3c","#3498db","#2ecc71","#f39c12",
            "#9b59b6","#1abc9c","#e67e22","#34495e",
        ]
        color_map_geo = {str(i): GEO_COLORS[i % len(GEO_COLORS)] for i in range(k_geo)}

        fig_geo_map = px.scatter_mapbox(
            df_cl,
            lat="Lat", lon="Lng",
            color="Geo_Cluster",
            color_discrete_map=color_map_geo,
            hover_name="Museum",
            hover_data={
                "Lat": False, "Lng": False,
                "Region": True,
                "Total_Visitors": ":,.0f",
                "Rating": ":.1f",
            },
            labels={"Geo_Cluster": "Ζώνη", "Total_Visitors": "Επισκέπτες", "Rating": "★"},
            size="Total_Visitors",
            size_max=30,
            mapbox_style="carto-positron",
            zoom=5.0,
            center={"lat": 38.9, "lon": 23.5},
            title=f"Γεωγραφικές Ζώνες Μουσείων (k={k_geo})",
        )
        fig_geo_map.update_layout(
            height=540,
            margin={"r":0,"t":40,"l":0,"b":0},
            legend=dict(title="Ζώνη", orientation="h", y=-0.08),
        )
        st.plotly_chart(fig_geo_map, use_container_width=True)

        # Σύνοψη ζωνών
        geo_summary = (
            df_cl.groupby("Geo_Cluster")
            .agg(
                Μουσεία            = ("Museum",         "count"),
                Περιοχές           = ("Region",         lambda x: " · ".join(x.value_counts().head(2).index)),
                Μέσ_Επισκέπτες    = ("Total_Visitors",  "mean"),
                Μέσ_Rating         = ("Rating",          "mean"),
            )
            .round({"Μέσ_Επισκέπτες": 0, "Μέσ_Rating": 2})
            .reset_index()
            .rename(columns={"Geo_Cluster": "Ζώνη"})
        )
        with st.expander("📋 Σύνοψη Γεωγραφικών Ζωνών"):
            st.dataframe(
                geo_summary.style.format({
                    "Μέσ_Επισκέπτες": "{:,.0f}",
                    "Μέσ_Rating":     "{:.2f}",
                }),
                use_container_width=True, hide_index=True,
            )

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — BEHAVIORAL CLUSTERING
    # ════════════════════════════════════════════════════════════════════
    with tab_beh:
        st.markdown(
            "Ομαδοποίηση με βάση το **προφίλ επισκεψιμότητας**: "
            "εποχικότητα, μέγεθος κοινού, ομοιομορφία ροής, Google Rating."
        )

        col_k, col_min = st.columns([1, 2])
        with col_k:
            k_beh = st.slider(
                "Αριθμός ομάδων (k):", min_value=3, max_value=6, value=4, key="k_beh",
            )
        with col_min:
            min_vis = st.slider(
                "Ελάχιστοι συνολικοί επισκέπτες (φίλτρο):",
                0, 50_000, 1_000, step=1_000, format="%,d",
            )

        df_beh = df_cl[df_cl["Total_Visitors"] >= min_vis].copy()

        BEH_FEATURES = ["Log_Visitors","CV","Summer_Pct","Winter_Pct","Spring_Pct","Rating"]
        BEH_LABELS   = ["log(Επισκ.)","Εποχικότητα","Καλοκαίρι","Χειμώνας","Άνοιξη","Rating"]

        scaler  = StandardScaler()
        beh_mat = scaler.fit_transform(df_beh[BEH_FEATURES].fillna(0))

        km_beh  = KMeans(n_clusters=k_beh, random_state=42, n_init=10)
        df_beh["Beh_Cluster"] = km_beh.fit_predict(beh_mat).astype(str)

        # Αυτόματη ετικέτα ανά cluster (με βάση χαρακτηριστικά)
        centers_orig = scaler.inverse_transform(km_beh.cluster_centers_)
        centers_df   = pd.DataFrame(centers_orig, columns=BEH_FEATURES)
        centers_df["k"] = range(k_beh)

        def auto_label(row):
            vis_raw = np.expm1(row["Log_Visitors"])
            if vis_raw > 1_500_000:
                return "🏛️ Πρωτεύοντα"
            elif row["Summer_Pct"] > 0.45:
                return "☀️ Καλοκαιρινά"
            elif row["Winter_Pct"] > 0.14 or row["CV"] < 0.85:
                return "🏙️ Σταθερά Αστικά"
            elif row["Rating"] < 4.0:
                return "⚠️ Χαμηλής Απόδοσης"
            else:
                return "🌿 Μεικτά"

        centers_df["Label"] = centers_df.apply(auto_label, axis=1)
        label_map = dict(zip(centers_df["k"].astype(str), centers_df["Label"]))
        df_beh["Cluster_Label"] = df_beh["Beh_Cluster"].map(label_map)

        BEH_COLORS = {
            "🏛️ Πρωτεύοντα":    "#2c3e50",
            "☀️ Καλοκαιρινά":   "#e67e22",
            "🏙️ Σταθερά Αστικά":"#2980b9",
            "⚠️ Υποαπόδοτα":    "#e74c3c",
            "🌿 Μεικτά":         "#27ae60",
        }

        col_radar, col_bar = st.columns([1, 1])

        with col_radar:
            # Radar chart για κάθε cluster
            import plotly.graph_objects as go

            radar_cols  = ["Summer_Pct","Winter_Pct","Spring_Pct","CV","Rating"]
            radar_names = ["Καλοκαίρι %","Χειμώνας %","Άνοιξη %","Εποχικότητα","Rating"]

            fig_radar = go.Figure()
            for _, crow in centers_df.iterrows():
                label  = crow["Label"]
                values = []
                for col, name in zip(radar_cols, radar_names):
                    v = crow[col]
                    if col in ("Summer_Pct","Autumn_Pct","Winter_Pct","Spring_Pct"):
                        v = round(v * 100, 1)         # → %
                    elif col == "Rating":
                        v = round((v - 3) / 2 * 100, 1)  # normalize 3-5 → 0-100
                    else:
                        v = round(min(v * 50, 100), 1)   # CV: 0-2 → 0-100
                    values.append(v)
                values.append(values[0])  # κλείσιμο polygon
                names_closed = radar_names + [radar_names[0]]

                fig_radar.add_trace(go.Scatterpolar(
                    r=values, theta=names_closed,
                    fill="toself", name=label,
                    line=dict(color=BEH_COLORS.get(label, "#7f8c8d")),
                    opacity=0.65,
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                legend=dict(orientation="h", y=-0.15),
                title="Προφίλ Ομάδων (Radar)",
                height=420,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_bar:
            # Bar chart: μέση επισκεψιμότητα ανά cluster
            beh_agg = (
                df_beh.groupby("Cluster_Label")
                .agg(
                    Μουσεία     =("Museum",         "count"),
                    Μέσ_Επισκ  =("Total_Visitors",  "mean"),
                    Μέσ_Rating  =("Rating",          "mean"),
                    Μέσ_Καλοκ  =("Summer_Pct",      "mean"),
                )
                .reset_index()
                .sort_values("Μέσ_Επισκ", ascending=False)
            )

            fig_beh_bar = px.bar(
                beh_agg,
                x="Cluster_Label", y="Μέσ_Επισκ",
                color="Cluster_Label",
                color_discrete_map=BEH_COLORS,
                text="Μουσεία",
                labels={
                    "Cluster_Label": "Κατηγορία",
                    "Μέσ_Επισκ": "Μέσοι Επισκέπτες",
                },
                title="Μέση Επισκεψιμότητα ανά Κατηγορία",
            )
            fig_beh_bar.update_traces(texttemplate="%{text} μουσεία", textposition="outside")
            fig_beh_bar.update_layout(
                showlegend=False, height=420,
                yaxis=dict(tickformat=",.0f"),
                xaxis_title="",
            )
            st.plotly_chart(fig_beh_bar, use_container_width=True)

        # Αναλυτικός πίνακας
        with st.expander("📋 Αναλυτικά Μουσεία ανά Κατηγορία"):
            tbl_beh = (
                df_beh[["Museum","Region","Cluster_Label",
                         "Total_Visitors","Rating","Summer_Pct","CV"]]
                .sort_values(["Cluster_Label","Total_Visitors"], ascending=[True, False])
                .reset_index(drop=True)
            )
            tbl_beh.index += 1
            st.dataframe(
                tbl_beh.style.format({
                    "Total_Visitors": "{:,.0f}",
                    "Rating":         "{:.1f}",
                    "Summer_Pct":     "{:.1%}",
                    "CV":             "{:.2f}",
                }),
                use_container_width=True, height=400,
            )

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 — ΣΥΝΔΥΑΣΤΙΚΟΣ ΧΑΡΤΗΣ
    # ════════════════════════════════════════════════════════════════════
    with tab_combo:
        st.markdown(
            "Τα μουσεία **στον χάρτη** χρωματίζονται με βάση την **behavioral κατηγορία** τους. "
            "Αποκαλύπτει αν παρόμοια μουσεία βρίσκονται κοντά γεωγραφικά ή διασκορπισμένα."
        )

        # Επαναλαμβάνουμε τo behavioral clustering για k=4 (σταθερό για τον χάρτη)
        df_combo = df_cl[df_cl["Total_Visitors"] >= 1000].copy()
        beh_mat2 = StandardScaler().fit_transform(df_combo[BEH_FEATURES].fillna(0))
        df_combo["Beh_Cluster"] = KMeans(n_clusters=4, random_state=42, n_init=10).fit_predict(beh_mat2).astype(str)

        # Ετικέτες με βάση χαρακτηριστικά cluster
        for c in df_combo["Beh_Cluster"].unique():
            sub = df_combo[df_combo["Beh_Cluster"]==c]
            lbl = auto_label(pd.Series({
                "Log_Visitors": sub["Log_Visitors"].mean(),
                "Summer_Pct":   sub["Summer_Pct"].mean(),
                "Winter_Pct":   sub["Winter_Pct"].mean(),
                "Rating":       sub["Rating"].mean(),
                "CV":           sub["CV"].mean(),
            }))
            df_combo.loc[df_combo["Beh_Cluster"]==c, "Cluster_Label"] = lbl

        fig_combo = px.scatter_mapbox(
            df_combo,
            lat="Lat", lon="Lng",
            color="Cluster_Label",
            color_discrete_map=BEH_COLORS,
            hover_name="Museum",
            hover_data={
                "Lat": False, "Lng": False,
                "Region":         True,
                "Total_Visitors": ":,.0f",
                "Rating":         ":.1f",
                "Summer_Pct":     ":.1%",
            },
            size="Total_Visitors",
            size_max=35,
            labels={
                "Cluster_Label":  "Κατηγορία",
                "Total_Visitors": "Επισκέπτες",
                "Rating":         "Rating ★",
                "Summer_Pct":     "Καλοκαίρι %",
            },
            mapbox_style="carto-positron",
            zoom=5.0,
            center={"lat": 38.9, "lon": 23.5},
            title="Γεωγραφική Κατανομή Behavioral Clusters",
        )
        fig_combo.update_layout(
            height=580,
            margin={"r":0,"t":40,"l":0,"b":0},
            legend=dict(title="Κατηγορία", orientation="h", y=-0.08),
        )
        st.plotly_chart(fig_combo, use_container_width=True)

        # Insight box
        st.info(
            "**Πώς να διαβάσεις τον χάρτη:** "
            "Αν τα καλοκαιρινά μουσεια βρίσκονται κυρίως σε νησιά και παράκτιες περιοχές, "
            "επιβεβαιώνεται ο τουριστικός χαρακτήρας τους. "
            "Αν τα σταθερά αστικά συγκεντρώνονται σε Αθήνα/Θεσσαλονίκη, "
            "επιβεβαιώνεται η αστική διάρθρωση της επισκεψιμότητας."
        )

# ═══════════════════════════════════════════════════════════════
# 17. ΣΥΝΔΥΑΣΤΙΚΗ ΑΝΑΛΥΣΗ ΕΠΙΣΚΕΨΙΜΟΤΗΤΑΣ & GOOGLE RATINGS
# ═══════════════════════════════════════════════════════════════
st.subheader("🔬 Συνδυαστική Ανάλυση Επισκεψιμότητας & Google Ratings")

if df_places.empty:
    st.info("Απαιτείται το αρχείο museums_place_ids.csv.")
else:
    # ── Προετοιμασία δεδομένων ────────────────────────────────────────────────
    visitors_total = (
        final_df.groupby("Museum")["Visitors"].sum()
        .reset_index()
        .rename(columns={"Visitors": "Total_Visitors"})
    )
    df_rv = df_places.merge(visitors_total, on="Museum", how="inner")
    df_rv = df_rv[df_rv["Rating"].notna() & df_rv["Total_Visitors"].notna()].copy()
    df_rv["Ratings_Total"] = pd.to_numeric(df_rv["Ratings_Total"], errors="coerce").fillna(0)

    # Ποσοστό κριτικών (reviews ανά 1000 επισκέπτες)
    df_rv["Review_Rate"] = (df_rv["Ratings_Total"] / df_rv["Total_Visitors"] * 1000).round(3)

    # Κατώφλια τεταρτημορίων (διάμεσος)
    med_rating   = df_rv["Rating"].median()
    med_visitors = df_rv["Total_Visitors"].median()

    # Ανάθεση τεταρτημορίου
    def assign_quadrant(row):
        hi_r = row["Rating"]        >= med_rating
        hi_v = row["Total_Visitors"] >= med_visitors
        if   hi_r and     hi_v: return "⭐ Αστέρια"
        elif hi_r and not hi_v: return "💎 Κρυμμένοι Θησαυροί"
        elif not hi_r and hi_v: return "⚠️ Τουριστική Παγίδα"
        else:                   return "📉 Χαμηλής Απόδοσης"

    df_rv["Quadrant"] = df_rv.apply(assign_quadrant, axis=1)

    QUAD_COLORS = {
        "⭐ Αστέρια":             "#2ecc71",
        "💎 Κρυμμένοι Θησαυροί": "#3498db",
        "⚠️ Τουριστική Παγίδα":  "#e74c3c",
        "📉 Χαμηλής Απόδοσης":   "#95a5a6",
    }

    # ── KPIs ──────────────────────────────────────────────────────────────────
    corr_val = df_rv["Rating"].corr(np.log1p(df_rv["Total_Visitors"]))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Μουσεία στην ανάλυση",  f"{len(df_rv)}")
    k2.metric("Μέση Βαθμολογία",       f"{df_rv['Rating'].mean():.2f} ★")
    k3.metric("Διάμεσος Επισκεπτών",   f"{med_visitors:,.0f}")
    k4.metric("Συσχέτιση Rating-Επισκ.", f"r = {corr_val:.2f}",
              help="Pearson r μεταξύ Rating και log(Επισκέπτες). Κοντά στο 0 = ασθενής συσχέτιση.")
    k5.metric("⭐ Αστέρια / 💎 Θησαυροί",
              f"{(df_rv['Quadrant']=='⭐ Αστέρια').sum()} / "
              f"{(df_rv['Quadrant']=='💎 Κρυμμένοι Θησαυροί').sum()}")

    st.caption(
        f"📌 Κατώφλι Βαθμολογίας: **{med_rating:.1f}** (διάμεσος) | "
        f"Κατώφλι Επισκεπτών: **{med_visitors:,.0f}** (διάμεσος)"
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_q, tab_corr, tab_silent, tab_region, tab_tbl = st.tabs([
        "🎯 Μήτρα Τεταρτημορίων",
        "📈 Συσχέτιση",
        "🤫 Αθόρυβοι Επισκέπτες",
        "🗺️ Ανά Περιφέρεια",
        "📋 Πλήρης Πίνακας",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — ΜΗΤΡΑ ΤΕΤΑΡΤΗΜΟΡΙΩΝ
    # ════════════════════════════════════════════════════════════════
    with tab_q:
        st.markdown(
            "Κάθε μουσείο κατηγοριοποιείται σε ένα από τα 4 τεταρτημόρια "
            "με βάση τη **βαθμολογία** και την **επισκεψιμότητά** του σε σχέση "
            "με τη διάμεσο τιμή."
        )

        # Legenda
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.success("⭐ **Αστέρια**\nΥψηλό rating & υψηλή επισκεψιμότητα")
        lc2.info("💎 **Κρυμμένοι Θησαυροί**\nΥψηλό rating & χαμηλή επισκεψιμότητα")
        lc3.error("⚠️ **Τουριστική Παγίδα**\nΧαμηλό rating & υψηλή επισκεψιμότητα")
        lc4.warning("📉 **Χαμηλής Απόδοσης**\nΧαμηλό rating & χαμηλή επισκεψιμότητα")

        fig_quad = px.scatter(
            df_rv,
            x="Rating",
            y="Total_Visitors",
            size="Ratings_Total",
            size_max=45,
            color="Quadrant",
            color_discrete_map=QUAD_COLORS,
            hover_name="Museum",
            hover_data={
                "Rating":         ":.1f",
                "Total_Visitors": ":,.0f",
                "Ratings_Total":  ":,.0f",
                "Review_Rate":    ":.2f",
                "Region":         True,
                "Quadrant":       False,
            },
            labels={
                "Rating":         "Google Rating ★",
                "Total_Visitors": "Σύνολο Επισκεπτών",
                "Ratings_Total":  "Αριθμός Κριτικών",
                "Review_Rate":    "Κριτικές / 1000 Επισκ.",
                "Region":         "Περιφέρεια",
            },
            log_y=True,
            title="Μήτρα Επισκεψιμότητας — Google Rating",
        )

        # Γραμμές κατωφλίων
        fig_quad.add_vline(
            x=med_rating, line_dash="dash", line_color="gray", line_width=1.5,
            annotation_text=f"Διάμεσος Rating: {med_rating:.1f}",
            annotation_position="top right", annotation_font_size=11,
        )
        fig_quad.add_hline(
            y=med_visitors, line_dash="dash", line_color="gray", line_width=1.5,
            annotation_text=f"Διάμεσος Επισκ.: {med_visitors:,.0f}",
            annotation_position="right", annotation_font_size=11,
        )
        fig_quad.update_layout(
            height=580,
            legend=dict(title="Κατηγορία", orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_quad, use_container_width=True)

        # Σύνοψη ανά τεταρτημόριο
        quad_summary = (
            df_rv.groupby("Quadrant")
            .agg(
                Μουσεία        =("Museum",         "count"),
                Μέσο_Rating    =("Rating",          "mean"),
                Μέσοι_Επισκέπτες=("Total_Visitors", "mean"),
                Σύνολο_Κριτικών=("Ratings_Total",  "sum"),
            )
            .round({"Μέσο_Rating": 2, "Μέσοι_Επισκέπτες": 0})
            .reset_index()
        )
        with st.expander("📊 Σύνοψη ανά Κατηγορία"):
            st.dataframe(
                quad_summary.style.format({
                    "Μέσο_Rating":         "{:.2f}",
                    "Μέσοι_Επισκέπτες":    "{:,.0f}",
                    "Σύνολο_Κριτικών":     "{:,.0f}",
                }),
                use_container_width=True,
            )

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — ΣΥΣΧΕΤΙΣΗ
    # ════════════════════════════════════════════════════════════════
    with tab_corr:
        col_l, col_r = st.columns([2, 1])

        with col_l:
            # Scatter με γραμμή τάσης (OLS)
            import numpy as np
            log_vis = np.log1p(df_rv["Total_Visitors"])
            z = np.polyfit(log_vis, df_rv["Rating"], 1)
            p = np.poly1d(z)
            x_line = np.linspace(log_vis.min(), log_vis.max(), 200)

            fig_corr = px.scatter(
                df_rv,
                x="Total_Visitors",
                y="Rating",
                color="Region",
                hover_name="Museum",
                hover_data={"Total_Visitors": ":,.0f", "Rating": ":.1f"},
                labels={
                    "Total_Visitors": "Σύνολο Επισκεπτών (log)",
                    "Rating":         "Google Rating ★",
                },
                log_x=True,
                title=f"Συσχέτιση Rating — Επισκεψιμότητα  (r = {corr_val:.2f})",
                opacity=0.75,
            )
            fig_corr.add_scatter(
                x=np.expm1(x_line), y=p(x_line),
                mode="lines",
                line=dict(color="black", dash="dot", width=2),
                name="Τάση (OLS)",
                showlegend=True,
            )
            fig_corr.update_layout(height=480, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_corr, use_container_width=True)

        with col_r:
            st.markdown("#### 💡 Ερμηνεία")
            st.markdown(
                f"Ο συντελεστής συσχέτισης **r = {corr_val:.2f}** δείχνει "
                f"ότι η βαθμολογία στο Google **δεν καθορίζει** σε σημαντικό βαθμό "
                f"τον αριθμό επισκεπτών.\n\n"
                f"Αυτό σημαίνει ότι:\n"
                f"- Η **φήμη/τοποθεσία** παίζει μεγαλύτερο ρόλο από την ποιότητα\n"
                f"- Υπάρχουν μουσεία με **εξαιρετική ποιότητα** που παραμένουν άγνωστα\n"
                f"- Τα μεγάλα αστικά μουσεία συγκεντρώνουν επισκέπτες ανεξάρτητα rating"
            )

            st.markdown("#### 📐 Στατιστικά")
            stats_df = pd.DataFrame({
                "Μέτρο": ["N", "r (log)", "Rating μέσος", "Rating std", "Rating min", "Rating max"],
                "Τιμή": [
                    len(df_rv),
                    f"{corr_val:.3f}",
                    f"{df_rv['Rating'].mean():.2f}",
                    f"{df_rv['Rating'].std():.2f}",
                    f"{df_rv['Rating'].min():.1f}",
                    f"{df_rv['Rating'].max():.1f}",
                ]
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — ΑΘΟΡΥΒΟΙ ΕΠΙΣΚΕΠΤΕΣ
    # ════════════════════════════════════════════════════════════════
    with tab_silent:
        st.markdown(
            "Μουσεία με **υψηλή επισκεψιμότητα αλλά ελάχιστες κριτικές** — "
            "οι επισκέπτες τα επισκέπτονται αλλά δεν τα αξιολογούν διαδικτυακά. "
            "Αυτά έχουν το μεγαλύτερο περιθώριο βελτίωσης ψηφιακής παρουσίας."
        )

        # Φίλτρο: μόνο μουσεία με αξιόλογη επισκεψιμότητα
        vis_threshold = st.slider(
            "Ελάχιστος αριθμός επισκεπτών:",
            min_value=10_000, max_value=500_000, value=50_000, step=10_000,
            format="%,d",
        )
        df_silent = (
            df_rv[df_rv["Total_Visitors"] >= vis_threshold]
            .sort_values("Review_Rate")
            .head(20)
            .copy()
        )

        fig_silent = px.bar(
            df_silent,
            x="Review_Rate",
            y="Museum",
            orientation="h",
            color="Rating",
            color_continuous_scale="RdYlGn",
            hover_data={
                "Total_Visitors": ":,.0f",
                "Ratings_Total":  ":,.0f",
                "Review_Rate":    ":.2f",
                "Region":         True,
            },
            labels={
                "Review_Rate":    "Κριτικές ανά 1.000 Επισκέπτες",
                "Museum":         "",
                "Rating":         "Rating ★",
                "Total_Visitors": "Επισκέπτες",
                "Ratings_Total":  "Κριτικές",
            },
            title="Top 20 «Αθόρυβα» Μουσεία — Χαμηλότερος Δείκτης Κριτικών/Επισκέπτες",
        )
        fig_silent.update_layout(
            height=580,
            yaxis={"categoryorder": "total ascending"},
            coloraxis_colorbar=dict(title="Rating ★"),
        )
        st.plotly_chart(fig_silent, use_container_width=True)

        st.caption(
            "📌 Ο δείκτης **Κριτικές / 1.000 Επισκέπτες** μετρά πόσοι επισκέπτες "
            "αφήνουν κριτική στο Google Maps. Χαμηλός δείκτης = ψηφιακά αόρατο μουσείο."
        )

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — ΑΝΑ ΠΕΡΙΦΕΡΕΙΑ
    # ════════════════════════════════════════════════════════════════
    with tab_region:
        col_box, col_bar = st.columns(2)

        with col_box:
            # Box plot ratings ανά περιφέρεια
            region_order = (
                df_rv.groupby("Region")["Rating"]
                .median()
                .sort_values(ascending=False)
                .index.tolist()
            )
            fig_box = px.box(
                df_rv,
                x="Rating",
                y="Region",
                points="all",
                color="Region",
                hover_name="Museum",
                category_orders={"Region": region_order},
                labels={"Rating": "Google Rating ★", "Region": "Περιφέρεια"},
                title="Κατανομή Ratings ανά Περιφέρεια",
            )
            fig_box.update_layout(
                height=560,
                showlegend=False,
                yaxis_title="",
            )
            st.plotly_chart(fig_box, use_container_width=True)

        with col_bar:
            # Stacked bar: σύνθεση τεταρτημορίων ανά περιφέρεια
            quad_by_region = (
                df_rv.groupby(["Region", "Quadrant"])
                .size()
                .reset_index(name="Count")
            )
            fig_stack = px.bar(
                quad_by_region,
                x="Count",
                y="Region",
                color="Quadrant",
                color_discrete_map=QUAD_COLORS,
                orientation="h",
                labels={"Count": "Μουσεία", "Region": "Περιφέρεια"},
                title="Σύνθεση Κατηγοριών ανά Περιφέρεια",
            )
            fig_stack.update_layout(
                height=560,
                yaxis={"categoryorder": "total ascending"},
                yaxis_title="",
                legend=dict(title="", orientation="h", y=-0.15),
            )
            st.plotly_chart(fig_stack, use_container_width=True)

        # Αναλυτικός πίνακας ανά περιφέρεια
        with st.expander("📋 Αναλυτικά ανά Περιφέρεια"):
            region_stats = (
                df_rv.groupby("Region")
                .agg(
                    Μουσεία         =("Museum",         "count"),
                    Μέσο_Rating     =("Rating",          "mean"),
                    Διάμεσος_Rating =("Rating",          "median"),
                    Σύνολο_Επισκ    =("Total_Visitors",  "sum"),
                    Σύνολο_Κριτικών =("Ratings_Total",   "sum"),
                )
                .round({"Μέσο_Rating": 2, "Διάμεσος_Rating": 2})
                .sort_values("Μέσο_Rating", ascending=False)
                .reset_index()
            )
            st.dataframe(
                region_stats.style.format({
                    "Μέσο_Rating":      "{:.2f}",
                    "Διάμεσος_Rating":  "{:.2f}",
                    "Σύνολο_Επισκ":     "{:,.0f}",
                    "Σύνολο_Κριτικών":  "{:,.0f}",
                }),
                use_container_width=True,
            )

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — ΠΛΗΡΗΣ ΠΙΝΑΚΑΣ
    # ════════════════════════════════════════════════════════════════
    with tab_tbl:
        # Φίλτρο κατηγορίας
        quad_filter = st.multiselect(
            "Φίλτρο κατηγορίας:",
            options=list(QUAD_COLORS.keys()),
            default=list(QUAD_COLORS.keys()),
        )
        df_show = df_rv[df_rv["Quadrant"].isin(quad_filter)].copy()
        df_show = df_show[[
            "Museum", "Region", "Rating", "Ratings_Total",
            "Total_Visitors", "Review_Rate", "Quadrant", "Google_Maps_URL"
        ]].sort_values("Total_Visitors", ascending=False).reset_index(drop=True)
        df_show.index += 1

        def color_quadrant(val):
            colors = {
                "⭐ Αστέρια":             "background-color:#d5f5e3",
                "💎 Κρυμμένοι Θησαυροί": "background-color:#d6eaf8",
                "⚠️ Τουριστική Παγίδα":  "background-color:#fadbd8",
                "📉 Χαμηλής Απόδοσης":   "background-color:#f2f3f4",
            }
            return colors.get(val, "")

        st.dataframe(
            df_show.style
            .format({
                "Rating":         "{:.1f}",
                "Ratings_Total":  "{:,.0f}",
                "Total_Visitors": "{:,.0f}",
                "Review_Rate":    "{:.2f}",
            })
            .map(color_quadrant, subset=["Quadrant"]),
            use_container_width=True,
            height=500,
        )
        st.caption(f"Εμφανίζονται {len(df_show)} από {len(df_rv)} μουσεία")

        excel_rv = to_excel(df_show.drop(columns=["Google_Maps_URL"], errors="ignore"))
        st.download_button(
            "📥 Λήψη Excel",
            data=excel_rv,
            file_name="museums_ratings_visitors.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.divider()

# ═══════════════════════════════════════════════════════════════
# 19. ΤΑΣΕΙΣ & ΠΡΟΒΛΕΨΕΙΣ
# ═══════════════════════════════════════════════════════════════
st.subheader("📈 Τάσεις & Προβλέψεις Επισκεψιμότητας")
st.markdown(
    "Γραμμική τάση και προβλέψεις 3 ετών. "
    "Τα έτη **2020–2021** εξαιρούνται από την εκτίμηση τάσης λόγω COVID."
)

from scipy import stats as _stats

COVID_YEARS = [2020, 2021]
FORECAST_YRS = [2026, 2027, 2028]
TREND_COLORS = {
    "Ανερχόμενο":  "#2ecc71",
    "Σταθερό":     "#3498db",
    "Φθίνον":      "#e74c3c",
}

# ── Βοηθητική: γραμμική τάση αγνοώντας COVID ────────────────────────────────
def fit_trend(series_by_year: pd.Series, exclude=COVID_YEARS):
    """series_by_year: index=Year, values=Visitors. Returns (slope, intercept, r2, se)."""
    s = series_by_year.drop(index=[y for y in exclude if y in series_by_year.index], errors="ignore")
    if len(s) < 4:
        return None
    slope, intercept, r, _, se = _stats.linregress(s.index.astype(int), s.values)
    return dict(slope=slope, intercept=intercept, r2=r**2, se=se, n=len(s))

def predict(trend, year):
    return trend["intercept"] + trend["slope"] * year

def classify_trend(pct_per_year):
    if pct_per_year > 3:  return "Ανερχόμενο"
    if pct_per_year < -3: return "Φθίνον"
    return "Σταθερό"

# ── Εθνικά δεδομένα ─────────────────────────────────────────────────────────
national_annual = (
    df.groupby("Year")["Visitors"].sum()
    .rename("Visitors")
)
nat_trend = fit_trend(national_annual)

tab_nat, tab_region, tab_museum, tab_rank = st.tabs([
    "🇬🇷 Εθνική Τάση",
    "🗺️ Ανά Περιφέρεια",
    "🏛️ Ανά Μουσείο",
    "📊 Ταξινόμηση Μουσείων",
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — ΕΘΝΙΚΗ ΤΑΣΗ
# ════════════════════════════════════════════════════════════════════
with tab_nat:
    # ── KPIs ────────────────────────────────────────────────────────
    last_actual   = int(national_annual.get(2024, national_annual.iloc[-1]))
    pred_2026     = int(predict(nat_trend, 2026))
    growth_abs    = int(nat_trend["slope"])
    growth_pct    = nat_trend["slope"] / national_annual[~national_annual.index.isin(COVID_YEARS)].mean() * 100

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Τελευταίο Έτος (2024)",   f"{last_actual:,.0f}")
    k2.metric("Πρόβλεψη 2026",            f"{pred_2026:,.0f}",
              delta=f"+{pred_2026 - last_actual:,.0f}")
    k3.metric("Ετήσια Αύξηση (τάση)",    f"+{growth_abs:,.0f} επισκ.")
    k4.metric("R² Γραμμικής Τάσης",       f"{nat_trend['r2']:.3f}",
              help="Πόσο καλά η ευθεία εξηγεί τη διακύμανση. >0.7 = ισχυρή τάση.")

    # ── Γράφημα: ιστορικά + τάση + πρόβλεψη ────────────────────────
    hist_df = national_annual.reset_index()
    hist_df.columns = ["Year", "Visitors"]
    hist_df["Τύπος"] = hist_df["Year"].apply(
        lambda y: "COVID (εξαίρεση)" if y in COVID_YEARS else "Πραγματικά"
    )

    # Γραμμή τάσης πάνω σε μη-COVID έτη
    trend_years = [y for y in hist_df["Year"] if y not in COVID_YEARS]
    trend_vals  = [predict(nat_trend, y) for y in trend_years]

    # Προβλέψεις με διάστημα εμπιστοσύνης (±1.96 * se * sqrt(1 + 1/n))
    se_pred = nat_trend["se"] * np.sqrt(1 + 1 / nat_trend["n"])
    z       = 1.96
    fc_df   = pd.DataFrame({
        "Year":    FORECAST_YRS,
        "Visitors": [predict(nat_trend, y) for y in FORECAST_YRS],
        "Lower":   [predict(nat_trend, y) - z * se_pred * abs(y - 2023) for y in FORECAST_YRS],
        "Upper":   [predict(nat_trend, y) + z * se_pred * abs(y - 2023) for y in FORECAST_YRS],
    })

    fig_nat = go.Figure()

    # Πραγματικές τιμές
    actual = hist_df[hist_df["Τύπος"] == "Πραγματικά"]
    covid  = hist_df[hist_df["Τύπος"] == "COVID (εξαίρεση)"]

    fig_nat.add_trace(go.Bar(
        x=actual["Year"], y=actual["Visitors"],
        name="Πραγματικά", marker_color="#3498db", opacity=0.8,
    ))
    fig_nat.add_trace(go.Bar(
        x=covid["Year"], y=covid["Visitors"],
        name="COVID (εξαίρεση)", marker_color="#e74c3c", opacity=0.6,
    ))

    # Γραμμή τάσης
    fig_nat.add_trace(go.Scatter(
        x=trend_years, y=trend_vals,
        mode="lines", name="Γραμμή Τάσης",
        line=dict(color="#f39c12", width=2.5, dash="dot"),
    ))

    # Διάστημα εμπιστοσύνης
    fig_nat.add_trace(go.Scatter(
        x=FORECAST_YRS + FORECAST_YRS[::-1],
        y=list(fc_df["Upper"]) + list(fc_df["Lower"][::-1]),
        fill="toself", fillcolor="rgba(46,204,113,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% Διάστημα", showlegend=True,
    ))

    # Προβλέψεις
    fig_nat.add_trace(go.Scatter(
        x=fc_df["Year"], y=fc_df["Visitors"],
        mode="lines+markers+text",
        name="Πρόβλεψη",
        line=dict(color="#2ecc71", width=3),
        marker=dict(size=9, symbol="diamond"),
        text=[f"{v:,.0f}" for v in fc_df["Visitors"]],
        textposition="top center",
        textfont=dict(size=11),
    ))

    fig_nat.update_layout(
        title="Εθνική Επισκεψιμότητα 1998–2028 (πρόβλεψη)",
        xaxis_title="Έτος",
        yaxis_title="Επισκέπτες",
        barmode="overlay",
        height=480,
        legend=dict(orientation="h", y=-0.2),
        yaxis=dict(tickformat=",.0f"),
    )
    st.plotly_chart(fig_nat, use_container_width=True)
    st.caption(
        "Η τάση υπολογίζεται με **γραμμική παλινδρόμηση** (OLS) εξαιρώντας τα COVID έτη. "
        "Το διάστημα εμπιστοσύνης ±95% διευρύνεται για μακρύτερες προβλέψεις."
    )

# ════════════════════════════════════════════════════════════════════
# TAB 2 — ΑΝΑ ΠΕΡΙΦΕΡΕΙΑ
# ════════════════════════════════════════════════════════════════════
with tab_region:
    region_annual = (
        df.groupby(["Year","Region"])["Visitors"].sum().reset_index()
    )

    # Τάση ανά περιφέρεια
    reg_trends = []
    for region in region_annual["Region"].unique():
        s = (region_annual[region_annual["Region"] == region]
             .set_index("Year")["Visitors"])
        t = fit_trend(s)
        if t is None:
            continue
        mean_vis = s[~s.index.isin(COVID_YEARS)].mean()
        pct = t["slope"] / max(mean_vis, 1) * 100
        reg_trends.append({
            "Region":       region,
            "slope":        t["slope"],
            "r2":           t["r2"],
            "pct_per_year": pct,
            "Τάση":         classify_trend(pct),
            "Pred_2026":    int(predict(t, 2026)),
            "Last_2024":    int(s.get(2024, s.iloc[-1])),
        })
    reg_df = pd.DataFrame(reg_trends).sort_values("pct_per_year", ascending=False)

    col_bars, col_map = st.columns([1, 1])

    with col_bars:
        fig_reg = px.bar(
            reg_df,
            x="pct_per_year", y="Region",
            orientation="h",
            color="Τάση",
            color_discrete_map=TREND_COLORS,
            text=reg_df["pct_per_year"].apply(lambda v: f"{v:+.1f}%/έτος"),
            labels={"pct_per_year": "Ετήσια μεταβολή %", "Region": ""},
            title="Ετήσια Τάση ανά Περιφέρεια",
        )
        fig_reg.update_traces(textposition="outside")
        fig_reg.update_layout(
            height=480, showlegend=True,
            xaxis=dict(tickformat=".1f", ticksuffix="%"),
            yaxis={"categoryorder": "total ascending"},
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_reg, use_container_width=True)

    with col_map:
        # Small-multiples: γραμμές τάσης ανά περιφέρεια
        fig_lines = px.line(
            region_annual,
            x="Year", y="Visitors",
            color="Region",
            title="Εξέλιξη ανά Περιφέρεια",
            labels={"Visitors": "Επισκέπτες", "Year": "Έτος"},
        )
        fig_lines.add_vrect(
            x0=2019.5, x1=2021.5,
            fillcolor="red", opacity=0.07,
            annotation_text="COVID", annotation_position="top left",
        )
        fig_lines.update_layout(
            height=480,
            legend=dict(orientation="h", y=-0.35, font_size=10),
            yaxis=dict(tickformat=",.0f"),
        )
        st.plotly_chart(fig_lines, use_container_width=True)

    # Πρόβλεψη 2026 ανά περιφέρεια
    with st.expander("📋 Πρόβλεψη 2026 ανά Περιφέρεια"):
        tbl_reg = reg_df[["Region","Last_2024","Pred_2026","pct_per_year","r2","Τάση"]].copy()
        tbl_reg["Delta"] = tbl_reg["Pred_2026"] - tbl_reg["Last_2024"]
        st.dataframe(
            tbl_reg.style.format({
                "Last_2024":    "{:,.0f}",
                "Pred_2026":    "{:,.0f}",
                "Delta":        "{:+,.0f}",
                "pct_per_year": "{:+.1f}%",
                "r2":           "{:.3f}",
            }).applymap(
                lambda v: f"color: {TREND_COLORS.get(v,'black')}" if isinstance(v,str) and v in TREND_COLORS else "",
                subset=["Τάση"]
            ),
            use_container_width=True, hide_index=True,
        )

# ════════════════════════════════════════════════════════════════════
# TAB 3 — ΑΝΑ ΜΟΥΣΕΙΟ (επιλογή)
# ════════════════════════════════════════════════════════════════════
with tab_museum:
    museum_options = sorted(
        df.groupby("Museum")["Visitors"].sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    sel_museum = st.selectbox(
        "Επέλεξε μουσείο:", museum_options, key="forecast_museum"
    )
    n_years_fc = st.slider("Έτη πρόβλεψης:", 1, 5, 3, key="fc_years")

    m_annual = (
        df[df["Museum"] == sel_museum]
        .groupby("Year")["Visitors"].sum()
        .rename("Visitors")
    )
    m_trend = fit_trend(m_annual)

    if m_trend is None:
        st.warning(f"Ανεπαρκή δεδομένα για το μουσείο '{sel_museum}' (χρειάζονται ≥4 έτη).")
    else:
        last_yr  = m_annual.index.max()
        fc_years = list(range(last_yr + 1, last_yr + 1 + n_years_fc))
        fc_vals  = [predict(m_trend, y) for y in fc_years]
        se_m     = m_trend["se"] * np.sqrt(1 + 1 / m_trend["n"])

        mean_vis_m   = m_annual[~m_annual.index.isin(COVID_YEARS)].mean()
        pct_m        = m_trend["slope"] / max(mean_vis_m, 1) * 100
        trend_label  = classify_trend(pct_m)
        trend_color  = TREND_COLORS[trend_label]

        # KPIs
        km1, km2, km3, km4 = st.columns(4)
        km1.metric("Τελευταία τιμή", f"{int(m_annual.iloc[-1]):,} ({last_yr})")
        km2.metric("Τάση", f"{pct_m:+.1f}%/έτος",
                   delta=trend_label,
                   delta_color="normal" if trend_label=="Ανερχόμενο" else
                               ("inverse" if trend_label=="Φθίνον" else "off"))
        km3.metric(f"Πρόβλεψη {fc_years[-1]}",
                   f"{int(predict(m_trend, fc_years[-1])):,}")
        km4.metric("R²", f"{m_trend['r2']:.3f}")

        # Γράφημα
        fig_m = go.Figure()

        act_x = [y for y in m_annual.index if y not in COVID_YEARS]
        act_y = [m_annual[y] for y in act_x]
        cov_x = [y for y in m_annual.index if y in COVID_YEARS]
        cov_y = [m_annual[y] for y in cov_x]

        fig_m.add_trace(go.Scatter(
            x=list(m_annual.index), y=list(m_annual.values),
            mode="lines+markers", name="Ιστορικά",
            line=dict(color="#3498db", width=2),
            marker=dict(size=6),
        ))
        if cov_x:
            fig_m.add_trace(go.Scatter(
                x=cov_x, y=cov_y, mode="markers",
                name="COVID", marker=dict(color="#e74c3c", size=10, symbol="x"),
            ))

        # Τάση (non-COVID)
        ty = list(range(m_annual.index.min(), last_yr + 1))
        fig_m.add_trace(go.Scatter(
            x=ty, y=[predict(m_trend, y) for y in ty],
            mode="lines", name="Τάση (OLS)",
            line=dict(color="#f39c12", dash="dot", width=2),
        ))

        # CI band
        ci_upper = [max(0, predict(m_trend,y) + z * se_m * (i+1)) for i,y in enumerate(fc_years)]
        ci_lower = [max(0, predict(m_trend,y) - z * se_m * (i+1)) for i,y in enumerate(fc_years)]
        fig_m.add_trace(go.Scatter(
            x=fc_years + fc_years[::-1],
            y=ci_upper + ci_lower[::-1],
            fill="toself", fillcolor="rgba(46,204,113,0.12)",
            line=dict(color="rgba(0,0,0,0)"), name="95% CI",
        ))

        fig_m.add_trace(go.Scatter(
            x=fc_years, y=fc_vals,
            mode="lines+markers+text", name="Πρόβλεψη",
            line=dict(color=trend_color, width=3),
            marker=dict(size=10, symbol="diamond"),
            text=[f"{int(v):,}" for v in fc_vals],
            textposition="top center",
        ))

        fig_m.add_vrect(
            x0=last_yr + 0.5, x1=fc_years[-1] + 0.5,
            fillcolor="rgba(46,204,113,0.05)",
            annotation_text="Πρόβλεψη", annotation_position="top left",
        )
        fig_m.update_layout(
            title=f"Τάση & Πρόβλεψη: {sel_museum}",
            xaxis_title="Έτος", yaxis_title="Επισκέπτες",
            height=460, legend=dict(orientation="h", y=-0.2),
            yaxis=dict(tickformat=",.0f"),
        )
        st.plotly_chart(fig_m, use_container_width=True)

        st.caption(
            f"Τάση: **{pct_m:+.1f}%/έτος** | "
            f"R² = {m_trend['r2']:.3f} | "
            f"Κλίση: {m_trend['slope']:+,.0f} επισκ./έτος. "
            "Εξαιρούνται 2020–2021 από την παλινδρόμηση."
        )

# ════════════════════════════════════════════════════════════════════
# TAB 4 — ΤΑΞΙΝΟΜΗΣΗ ΟΛΩΝ ΤΩΝ ΜΟΥΣΕΙΩΝ
# ════════════════════════════════════════════════════════════════════
with tab_rank:
    st.markdown("Ταξινόμηση όλων των μουσείων ανά κατηγορία τάσης.")

    # Υπολογισμός τάσης για όλα τα μουσεία
    @st.cache_data
    def compute_all_trends():
        results = []
        for museum in df["Museum"].unique():
            s = df[df["Museum"]==museum].groupby("Year")["Visitors"].sum()
            t = fit_trend(s)
            if t is None:
                continue
            mean_v = s[~s.index.isin(COVID_YEARS)].mean()
            pct    = t["slope"] / max(mean_v, 1) * 100
            results.append({
                "Museum":        museum,
                "Τάση":          classify_trend(pct),
                "pct_per_year":  round(pct, 2),
                "slope":         int(t["slope"]),
                "r2":            round(t["r2"], 3),
                "Last_Visitors": int(s.iloc[-1]),
                "Pred_2026":     int(max(0, predict(t, 2026))),
            })
        return pd.DataFrame(results)

    all_trends = compute_all_trends()

    # Φίλτρο κατηγορίας
    trend_filter = st.multiselect(
        "Εμφάνιση κατηγοριών:",
        ["Ανερχόμενο","Σταθερό","Φθίνον"],
        default=["Ανερχόμενο","Σταθερό","Φθίνον"],
        key="trend_filter",
    )

    col_chart, col_info = st.columns([2, 1])

    with col_info:
        counts = all_trends["Τάση"].value_counts()
        for label, color in TREND_COLORS.items():
            n = counts.get(label, 0)
            st.metric(label, f"{n} μουσεία",
                      delta=f"{n/len(all_trends)*100:.0f}% του συνόλου",
                      delta_color="off")

    with col_chart:
        top_n = st.slider("Εμφάνιση top-N ανά κατηγορία:", 5, 20, 10, key="top_n")
        parts = []
        for label in ["Ανερχόμενο","Σταθερό","Φθίνον"]:
            if label not in trend_filter:
                continue
            sub = all_trends[all_trends["Τάση"]==label]
            if label == "Φθίνον":
                parts.append(sub.nsmallest(top_n, "pct_per_year"))
            else:
                parts.append(sub.nlargest(top_n, "pct_per_year"))
        if parts:
            plot_df = pd.concat(parts).sort_values("pct_per_year")
            fig_rank = px.bar(
                plot_df,
                x="pct_per_year", y="Museum",
                orientation="h",
                color="Τάση",
                color_discrete_map=TREND_COLORS,
                text=plot_df["pct_per_year"].apply(lambda v: f"{v:+.1f}%"),
                labels={"pct_per_year":"Ετήσια μεταβολή %","Museum":""},
                title=f"Top {top_n} μουσεία ανά κατηγορία τάσης",
            )
            fig_rank.update_traces(textposition="outside")
            fig_rank.update_layout(
                height=max(350, len(plot_df)*26),
                showlegend=False,
                xaxis=dict(tickformat=".1f", ticksuffix="%"),
                yaxis={"categoryorder":"total ascending"},
                margin=dict(l=200),
            )
            st.plotly_chart(fig_rank, use_container_width=True)

    # Πλήρης πίνακας
    with st.expander("📋 Πλήρης Πίνακας Τάσεων"):
        show_df = all_trends[all_trends["Τάση"].isin(trend_filter)].sort_values(
            "pct_per_year", ascending=False
        ).reset_index(drop=True)
        show_df.index += 1
        st.dataframe(
            show_df.style.format({
                "pct_per_year":  "{:+.2f}%",
                "slope":         "{:+,.0f}",
                "r2":            "{:.3f}",
                "Last_Visitors": "{:,.0f}",
                "Pred_2026":     "{:,.0f}",
            }).applymap(
                lambda v: f"color: {TREND_COLORS.get(v,'black')}" if isinstance(v,str) and v in TREND_COLORS else "",
                subset=["Τάση"]
            ),
            use_container_width=True, height=450,
        )
        excel_trends = to_excel(show_df)
        st.download_button(
            "📥 Λήψη Excel", data=excel_trends,
            file_name="museum_trends.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
