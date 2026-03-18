import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

def calculate_gini(array):
    """Υπολογισμός δείκτη Gini για την κατανομή επισκεπτών"""
    array = array.flatten()
    if np.any(array < 0):
        array -= np.min(array)
    array += 0.0000001 # αποφυγή διαίρεσης με το μηδέν
    array = np.sort(array)
    index = np.arange(1, array.shape[0] + 1)
    n = array.shape[0]
    return ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array)))

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

st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🗓️ Δείκτης Εποχικότητας ανά Μήνα")
    # Υπολογισμός μέσου όρου ανά μήνα vs συνολικού μέσου όρου
    monthly_avg = final_df.groupby('Month')['Visitors'].mean()
    overall_avg = final_df['Visitors'].mean()
    seasonality_index = (monthly_avg / overall_avg)
    
    fig_season = px.bar(seasonality_index, labels={'value': 'Δείκτης', 'Month': 'Μήνας'},
                        title="1.0 = Μέσος Όρος (Πάνω από 1.0 σημαίνει Peak Season)",
                        color=seasonality_index, color_continuous_scale='Viridis')
    st.plotly_chart(fig_season, use_container_width=True)

with col_b:
    st.subheader("📉 Δείκτης Ανισότητας Gini")
    if selected_museum == "Όλα":
        # Υπολογισμός για όλα τα μουσεία στο φίλτρο
        visitor_array = final_df.groupby('Museum')['Visitors'].sum().values
        gini_val = calculate_gini(visitor_array)
        
        st.metric("Gini Coefficient", f"{gini_val:.3f}")
        st.info(f"Ο δείκτης {gini_val:.3f} δείχνει πόσο συγκεντρωμένοι είναι οι επισκέπτες σε λίγα μουσεία. Τιμές κοντά στο 1 υποδηλώνουν ανάγκη για προώθηση των λιγότερο γνωστών μουσείων.")
        
        # Προαιρετικά: Γράφημα Lorenz (Η οπτική αναπαράσταση του Gini)
        sorted_visitors = np.sort(visitor_array)
        cum_visitors = np.cumsum(sorted_visitors) / np.sum(sorted_visitors)
        fig_lorenz = px.area(x=np.linspace(0, 1, len(cum_visitors)), y=cum_visitors, 
                             title="Καμπύλη Lorenz (Κατανομή Επισκεπτών)")
        fig_lorenz.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dash"))
        st.plotly_chart(fig_lorenz, use_container_width=True)
    else:
        st.write("Επιλέξτε 'Όλα' στα μουσεία για να δείτε τον δείκτη ανισότητας στην αγορά.")

# 4. Αναλυτικός Πίνακας & Download
st.subheader("📋 Αναλυτικά Στοιχεία (Πίνακας)")
st.dataframe(final_df[['Region', 'Museum', 'Year', 'Month', 'Visitors']], use_container_width=True)

# Δημιουργία CSV με κωδικοποίηση UTF-8 και προσθήκη BOM για το Excel
csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

st.download_button(
    label="📥 Λήψη επιλεγμένων δεδομένων σε CSV (Ελληνικά)",
    data=csv,
    file_name='museum_data_filtered.csv',
    mime='text/csv',
)
