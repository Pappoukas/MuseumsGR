import streamlit as st
import pandas as pd
import plotly.express as px

# Ρύθμιση σελίδας
st.set_page_config(page_title="Hellenic Museums Analytics", layout="wide")

# Φόρτωση Δεδομένων
@st.cache_data
def load_data():
    df = pd.read_csv('MuseumsGR.csv')
    return df

df = load_data()

# --- SIDEBAR / ΜΕΝΟΥ ΕΠΙΛΟΓΩΝ ---
st.sidebar.header("Φίλτρα Ανάλυσης")
museum_list = df['Μουσείο'].unique().tolist()
selected_museum = st.sidebar.selectbox("Επιλέξτε Μουσείο", ["Όλα"] + museum_list)

# Φίλτρο Ετών (Υποθέτοντας ότι οι στήλες σας είναι τα έτη)
years = [str(year) for year in range(1998, 2026)]
selected_years = st.sidebar.multiselect("Επιλέξτε Έτη", years, default=["2023", "2024", "2025"])

# --- ΕΠΕΞΕΡΓΑΣΙΑ ΔΕΔΟΜΕΝΩΝ ---
if selected_museum != "Όla":
    filtered_df = df[df['Μουσείο'] == selected_museum]
else:
    filtered_df = df

# --- ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ ---
st.title("📊 Dashboard Επισκεψιμότητας Μουσείων (1998-2025)")
st.markdown(f"Ανάλυση για: **{selected_museum}**")

# 1. Περιγραφική Στατιστική (KPIs)
col1, col2, col3 = st.columns(3)
total_visitors = filtered_df[selected_years].sum().sum()
avg_visitors = filtered_df[selected_years].mean().mean()

col1.metric("Συνολικοί Επισκέπτες (Επιλεγμένα Έτη)", f"{total_visitors:,.0f}")
col2.metric("Μέσος Όρος ανά Μήνα", f"{avg_visitors:,.2f}")
col3.metric("Αριθμός Μουσείων", len(filtered_df))

# 2. Γράφημα Τάσεων (Time Series)
st.subheader("📈 Διαχρονική Τάση Επισκεψιμότητας")
# Αναδιάταξη δεδομένων για γράφημα (Melting)
df_melted = filtered_df.melt(id_vars=['Μουσείο'], value_vars=selected_years, 
                             var_name='Έτος', value_name='Επισκέπτες')
fig = px.line(df_melted, x='Έτος', y='Επισκέπτες', color='Μουσείο', 
              title="Εξέλιξη ανά Έτος", markers=True)
st.plotly_chart(fig, use_container_width=True)

# 3. Συγκριτικός Πίνακας
st.subheader("📋 Αναλυτικά Στοιχεία")
st.dataframe(filtered_df[['Μουσείο'] + selected_years], use_container_width=True)

# 4. Insight: Top 10 Μουσεία
if selected_museum == "Όλα":
    st.subheader("🏆 Top 10 Μουσεία σε Επισκεψιμότητα")
    top_10 = df.assign(Total=df[selected_years].sum(axis=1)).sort_values(by='Total', ascending=False).head(10)
    fig_bar = px.bar(top_10, x='Μουσείο', y='Total', color='Total', title="Κατάταξη βάσει επιλεγμένων ετών")
    st.plotly_chart(fig_bar, use_container_width=True)

# Προσθήκη κουμπιού εξαγωγής δεδομένων (CSV)
st.sidebar.markdown("---")
csv = filtered_df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    label="📥 Λήψη δεδομένων σε CSV",
    data=csv,
    file_name='museum_data_filtered.csv',
    mime='text/csv',
)
