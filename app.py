import streamlit as st
import pandas as pd
import plotly.express as px

# Ρύθμιση σελίδας
st.set_page_config(page_title="Hellenic Museums Analytics", layout="wide")

# Φόρτωση Δεδομένων
@st.cache_data
def load_data():
    # Φόρτωση με το σωστό διαχωριστικό (sep=';')
    df = pd.read_csv('MuseumsGR.csv', sep=';')
    # Δημιουργία στήλης Ημερομηνίας για καλύτερα γραφήματα
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str) + '-01')
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Σφάλμα κατά τη φόρτωση του αρχείου: {e}")
    st.stop()

# --- SIDEBAR / ΜΕΝΟΥ ΕΠΙΛΟΓΩΝ ---
st.sidebar.header("📊 Φίλτρα Αναζήτησης")

# Φίλτρο Περιφέρειας
region_list = sorted(df['Region'].unique().tolist())
selected_region = st.sidebar.multiselect("Επιλέξτε Περιφέρεια", region_list, default=region_list)

# Φιλτράρισμα βάσει Περιφέρειας για το επόμενο φίλτρο
df_filtered_reg = df[df['Region'].isin(selected_region)]

# Φίλτρο Μουσείου
museum_list = sorted(df_filtered_reg['Museum'].unique().tolist())
selected_museum = st.sidebar.selectbox("Επιλέξτε συγκεκριμένο Μουσείο", ["Όλα"] + museum_list)

# Φίλτρο Ετών
min_year = int(df['Year'].min())
max_year = int(df['Year'].max())
selected_years = st.sidebar.slider("Επιλέξτε Εύρος Ετών", min_year, max_year, (2015, max_year))

# Εφαρμογή όλων των φίλτρων στο τελικό DataFrame
final_df = df_filtered_reg[(df_filtered_reg['Year'] >= selected_years[0]) & (df_filtered_reg['Year'] <= selected_years[1])]

if selected_museum != "Όλα":
    final_df = final_df[final_df['Museum'] == selected_museum]

# --- ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ ---
st.title("🏛️ Στοιχεία Επισκεψιμότητας Μουσείων")
st.markdown(f"Ανάλυση δεδομένων ΕΛΣΤΑΤ για την περίοδο **{selected_years[0]} - {selected_years[1]}**")

# 1. Περιγραφική Στατιστική (KPIs)
col1, col2, col3 = st.columns(3)
total_vists = final_df['Visitors'].sum()
avg_monthly = final_df['Visitors'].mean()
museum_count = final_df['Museum'].nunique()

col1.metric("Συνολικοί Επισκέπτες", f"{total_vists:,.0f}")
col2.metric("Μέσος Όρος Επισκεπτών/Μήνα", f"{avg_monthly:,.0f}")
col3.metric("Αριθμός Μουσείων στο Φίλτρο", museum_count)

# 2. Γράφημα Τάσεων (Time Series)
st.subheader("📈 Διαχρονική Εξέλιξη")
# Ομαδοποίηση ανά ημερομηνία για το γράφημα
trend_data = final_df.groupby('Date')['Visitors'].sum().reset_index()
fig = px.line(trend_data, x='Date', y='Visitors', title="Συνολική Κίνηση ανά Μήνα", 
              line_shape='spline', render_mode='svg')
fig.update_traces(line_color='#0077b6')
st.plotly_chart(fig, use_container_width=True)

# 3. Σύγκριση Περιφερειών (Αν είναι επιλεγμένα "Όλα" τα μουσεία)
if selected_museum == "Όλα":
    st.subheader("🌍 Επισκεψιμότητα ανά Περιφέρεια")
    reg_data = final_df.groupby('Region')['Visitors'].sum().sort_values(ascending=True).reset_index()
    fig_reg = px.bar(reg_data, x='Visitors', y='Region', orientation='h', 
                     title="Κατάταξη Περιφερειών", color='Visitors', color_continuous_scale='Blues')
    st.plotly_chart(fig_reg, use_container_width=True)

# 4. Αναλυτικός Πίνακας & Download
st.subheader("📋 Αναλυτικά Στοιχεία (Πίνακας)")
st.dataframe(final_df[['Region', 'Museum', 'Year', 'Month', 'Visitors']], use_container_width=True)

csv = final_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Λήψη επιλεγμένων δεδομένων σε CSV",
    data=csv,
    file_name='museum_data_filtered.csv',
    mime='text/csv',
)
