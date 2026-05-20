# -*- coding: utf-8 -*-
"""
Created on Wed May 20 12:37:50 2026

@author: bvasconcelos
"""

import streamlit as st
import requests
import pandas as pd
import io

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Macro Dashboard", page_icon="📊", layout="wide")

# 2. VISUAL HEADER
st.title("📊 High-Frequency Macroeconomic Monitor")
st.markdown("This dashboard consumes the CEIC API in real-time, calculating data ingestion latency against official IBGE/BCB release schedules.")
st.divider()

# 3. CREDENTIALS AND IDS
TOKEN = "gKRDgGCA6FxeEeKfJYlny5zKmoIkxLrWwiJkrjbw6kmilOwFxb9aXEr5sNcawJQw6o6CnCRrvHGxWfDj23GHZZnQKn0MgMFo2yu6aR7heDjbpTmMosM4QhuC4z7jniPT"
headers = {"Authorization": TOKEN, "Accept": "application/json"}

lista_de_ids = [
    "273491403", "544340267", "366987777", "475685597", 
    "505769527", "505767847", "505786577", "505786857", 
    "505806137", "240785002"
]

# 4. DATA INGESTION FUNCTION
@st.cache_data(ttl=3600) 
def carregar_dados_ceic():
    lista_resultados = []
    df_historico_ipca = pd.DataFrame()
    
    for sid in lista_de_ids:
        # Metadata Fetch
        resp_meta = requests.get(f"https://api.ceicdata.com/v2/series/{sid}", headers=headers).json()
        item_meta = resp_meta.get("data", [{}])[0] if isinstance(resp_meta.get("data"), list) else resp_meta.get("data", {})
        nome_ind = item_meta.get("metadata", {}).get("name", f"ID {sid}")
        att_bruto = item_meta.get("metadata", {}).get("timepointsLastUpdateTime")
        
        # Time Series Data Fetch
        resp_data = requests.get(f"https://api.ceicdata.com/v2/series/{sid}/data", headers=headers, params={"startDate": "2024-01-01"}).json()
        pontos = resp_data.get("data", [{}])[0].get("timePoints", []) if isinstance(resp_data.get("data"), list) else resp_data.get("data", {}).get("timePoints", [])
        
        if pontos:
            df_temp = pd.DataFrame(pontos)
            df_temp['date'] = pd.to_datetime(df_temp['date'])
            df_temp = df_temp.sort_values(by='date', ascending=True).reset_index(drop=True)
            
            valor_bruto = df_temp.iloc[-1]['value']
            ultimo_valor = f"{valor_bruto:,.4f}" 
            
            # Save IPCA for the chart
            if sid == "273491403":
                df_historico_ipca = df_temp[['date', 'value']].set_index('date')
        else:
            ultimo_valor = "N/A"

        # Latency Calculation
        if att_bruto and "T" in att_bruto:
            horario_sp = pd.to_datetime(att_bruto).tz_convert('America/Sao_Paulo')
            horario_oficial = horario_sp.replace(hour=9, minute=0, second=0, microsecond=0)
            atraso = (horario_sp - horario_oficial).total_seconds()
            
            if atraso < 0:
                latencia_str = "🟢 Early Release"
            else:
                latencia_str = f"🔴 {int(atraso // 60)}m {int(atraso % 60)}s"
        else:
            latencia_str = "Unknown"
            
        lista_resultados.append({
            "Indicator": nome_ind,
            "Latest Value": ultimo_valor,
            "API Latency": latencia_str,
            "Last Updated": horario_sp.strftime('%Y-%m-%d %H:%M') if 'horario_sp' in locals() else "-"
        })
        
    return pd.DataFrame(lista_resultados), df_historico_ipca

# 5. RENDERING THE INTERFACE
with st.spinner("Connecting to CEIC Data API..."):
    df_tabela, df_ipca = carregar_dados_ceic()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Data Ingestion & Latency Audit")
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    
    # --- NOVOS BOTÕES DE AÇÃO ---
    btn_col1, btn_col2 = st.columns(2)
    
    # Botão 1: Limpar o cache e tentar buscar a série indisponível novamente
    with btn_col1:
        if st.button("🔄 Force Refresh (Clear Cache)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    # Botão 2: Gerar e baixar o arquivo Excel
    with btn_col2:
        if not df_tabela.empty:
            buffer = io.BytesIO()
            # Usamos o openpyxl nativo do Pandas para montar a planilha em memória
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_tabela.to_excel(writer, index=False, sheet_name='Dashboard Data')
            
            st.download_button(
                label="📥 Download as Excel",
                data=buffer.getvalue(),
                file_name="Macro_Dashboard_Export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

with col2:
    st.subheader("Trend - IPCA: General")
    if not df_ipca.empty:
        st.line_chart(df_ipca)
    else:
        st.info("Chart data currently unavailable.")

