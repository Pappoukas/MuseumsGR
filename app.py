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
df = load_data()

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
row2_col1.metric("Μέσος όρος / Μήνα",         f"{monthly_avg:,.0f}")
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

    tab_abs, tab_norm, tab_pct = st.tabs([
    "Απόλυτα", 
    "Ανά Μουσείο", 
    "Ποσοστά %"
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
        reg_data['Ποσοστό (%)'] = (
            reg_data['Visitors'] / reg_data['Visitors'].sum() * 100
        ).round(2)

        fig_pct = px.bar(
            reg_data.sort_values('Ποσοστό (%)'),
            x='Ποσοστό (%)', y='Region', orientation='h',
            title="Μερίδιο Επισκεψιμότητας ανά Περιφέρεια (%)",
            color='Ποσοστό (%)', color_continuous_scale='Blues',
            text='Ποσοστό (%)'
        )
        fig_pct.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        st.plotly_chart(fig_pct, use_container_width=True)

        # Και ο πίνακας
        st.dataframe(
            reg_data[['Region','Visitors','Ποσοστό (%)']]\
                .sort_values('Ποσοστό (%)', ascending=False)\
                .reset_index(drop=True),
            use_container_width=True
        )

st.divider()

# ═════════════════════════════════════════════
# 11. ΑΝΑΛΥΤΙΚΟΣ ΠΙΝΑΚΑΣ & DOWNLOAD
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
