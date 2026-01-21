import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SPC Color Dashboard", layout="wide")
st.title("SPC Dashboard - LAB vs LINE")

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv","xlsx"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("File loaded successfully!")
    st.dataframe(df.head(5))

    df['ΔE_avg'] = df[['ΔE_北','ΔE_南']].mean(axis=1)
    df['ΔL_avg'] = df[['ΔL_北','ΔL_南']].mean(axis=1)
    df['Δa_avg'] = df[['Δa_北','Δa_南']].mean(axis=1)
    df['Δb_avg'] = df[['Δb_北','Δb_南']].mean(axis=1)

    batch_line = df.groupby('Batch').agg({
        'ΔE_avg':'mean',
        'ΔL_avg':'mean',
        'Δa_avg':'mean',
        'Δb_avg':'mean'
    }).reset_index()
    st.subheader("Batch-level LINE Average")
    st.dataframe(batch_line)

    if 'ΔE_LAB' in df.columns:
        batch_lab = df.groupby('Batch').agg({
            'ΔE_LAB':'first',
            'ΔL_LAB':'first',
            'Δa_LAB':'first',
            'Δb_LAB':'first'
        }).reset_index()
        comparison = batch_line.merge(batch_lab, on='Batch')
        comparison['ΔE_diff'] = comparison['ΔE_avg'] - comparison['ΔE_LAB']
        comparison['ΔL_diff'] = comparison['ΔL_avg'] - comparison['ΔL_LAB']
        st.subheader("Batch-level LINE vs LAB")
        st.dataframe(comparison)

    st.subheader("ΔN–S Alerts per Coil")
    df['ΔE_NS'] = abs(df['ΔE_北'] - df['ΔE_南'])
    df['ΔE_alert'] = pd.cut(df['ΔE_NS'], bins=[-0.01,0.1,0.2,10], labels=["OK","Warning","NG"])
    st.dataframe(df[['Coil_No','Batch','ΔE_NS','ΔE_alert']])

    fig = px.line(comparison, x='Batch', y=['ΔE_LAB','ΔE_avg'], labels={'value':'ΔE','variable':'Source'}, title="SPC ΔE LAB vs LINE")
    fig.update_traces(mode='lines+markers')
    st.plotly_chart(fig, use_container_width=True)
