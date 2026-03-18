import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Ρύθμιση σελίδας
st.set_page_config(page_title="Hellenic Museums Analytics", layout="wide")

# Συναρτήσεις Ανάλυσης
def calculate_gini(array):
    """Υπολογισμός δείκτη Gini (0=Ισότητα, 1=Απόλυτη Ανισότητα)"""
    array = array.flatten()
    if np.any(array < 0): array -= np.min(array)
    array = np.sort(array + 0.000001)
    n = array.shape[0]
    index = np.arange(1, n + 1)
    return ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array)))

@st.cache_data
def load_data():
    df = pd.read_csv('MuseumsGR.csv', sep=';')
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str) + '-01')
    return df

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("📊 Φίλτρα Ανάλυσης")
region_list = sorted(df['Region'].unique().tolist())
selected_region = st.sidebar.multiselect("Περιφέρειες", region_list, default=region_list)

df_filt = df[df['Region'].isin(selected_region)]
museum_list = sorted(df_filt['Museum'].unique().tolist())
selected_museum = st.sidebar.selectbox("Μουσείο", ["Όλα"] + museum_list)

years = sorted(df['Year'].unique().tolist())
selected_years = st.sidebar.slider("Έτη", min(years), max(years), (2018, max(years)))

# Εφαρμογή Φίλτρων
final_df = df_filt[(df_filt['Year'] >= selected_years[0]) & (df_filt['Year'] <= selected_years[1])]
if selected_museum != "Όλα":
    final_df = final_df[final_df['Museum'] == selected_museum]

# --- MAIN DASHBOARD ---
st.title("🏛️ Ανάλυση Επισκεψιμότητας Ελληνικών Μουσείων (1998-2025)")

# KPIs
c1, c2, c3 = st.columns(3)
c1.metric("Συνολικοί Επισκέπτες", f"{final_df['Visitors'].sum():,.0f}")
c2.metric("Μέσος Όρος/Μήνα", f"{final_df['Visitors'].mean():,.0f}")
c3.metric("Πλήθος Μουσείων", final_df['Museum'].nunique())

st.divider()

# Γράφημα Τάσης
st.subheader("📈 Χρονοσειρά Επισκεψιμότητας")
trend = final_df.groupby('Date')['Visitors'].sum().reset_index()
fig_trend = px.line(trend, x='Date', y='Visitors', line_shape='spline')
st.plotly_chart(fig_trend, use_container_width=True)

# --- ΕΠΟΧΙΚΟΤΗΤΑ & GINI ---
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🗓️ Δείκτης Εποχικότητας")
    # Υπολογισμός: (Μέσος Μήνα / Συνολικός Μέσος)
    m_avg = final_df.groupby('Month')['Visitors'].mean()
    overall_avg = final_df['Visitors'].mean()
    s_index = m_avg / overall_avg
    
    fig_s = px.bar(x=s_index.index, y=s_index.values, labels={'x':'Μήνας', 'y':'Δείκτης'},
                   title="Τιμές > 1.0 υποδηλώνουν Υψηλή Περίοδο", color=s_index.values)
    st.plotly_chart(fig_s, use_container_width=True)

with col_right:
    st.subheader("📉 Ανάλυση Ανισότητας (Gini)")
    if selected_museum == "Όλα":
        dist = final_df.groupby('Museum')['Visitors'].sum().values
        g_val = calculate_gini(dist)
        st.metric("Δείκτης Gini", f"{g_val:.3f}")
        st.caption("0 = Ισοκατανομή | 1 = Συγκέντρωση σε λίγα μουσεία")
        
        # Lorenz Curve
        sorted_dist = np.sort(dist)
        lorenz = np.cumsum(sorted_dist) / np.sum(sorted_dist)
        fig_l = px.area(x=np.linspace(0, 1, len(lorenz)), y=lorenz, title="Καμπύλη Lorenz")
        fig_l.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dash", color="red"))
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.info("Ο δείκτης Gini υπολογίζεται μόνο για τη σύγκριση πολλαπλών μουσείων.")

# Σύγκριση Περιφερειών (Αν είναι επιλεγμένα "Όλα" τα μουσεία)
if selected_museum == "Όλα":
    st.subheader("🌍 Επισκεψιμότητα ανά Περιφέρεια")
    reg_data = final_df.groupby('Region')['Visitors'].sum().sort_values(ascending=True).reset_index()
    fig_reg = px.bar(reg_data, x='Visitors', y='Region', orientation='h', 
                     title="Κατάταξη Περιφερειών", color='Visitors', color_continuous_scale='Blues')
    st.plotly_chart(fig_reg, use_container_width=True)

# 4. Αναλυτικός Πίνακας & Download
st.subheader("📋 Αναλυτικά Στοιχεία (Πίνακας)")
st.dataframe(final_df[['Region', 'Museum', 'Year', 'Month', 'Visitors']], use_container_width=True)

# Download
csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
st.download_button("📥 Λήψη Δεδομένων (UTF-8)", data=csv, file_name='museum_stats.csv')
