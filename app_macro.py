# -*- coding: utf-8 -*-
"""
Created on Wed May 20 12:37:50 2026

@author: bvasconcelos
"""

import streamlit as st
import requests
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Macro Dashboard", page_icon="📊", layout="wide")

# 2. CABEÇALHO VISUAL
st.title("📊 Monitoramento Macroeconômico de Alta Frequência")
st.markdown("Este painel consome a API do CEIC em tempo real, calculando a latência de ingestão frente aos horários oficiais do IBGE/BCB.")
st.divider()

# 3. CREDENCIAIS E IDS (AGORA COM OS 10 INDICADORES!)
TOKEN = "gKRDgGCA6FxeEeKfJYlny5zKmoIkxLrWwiJkrjbw6kmilOwFxb9aXEr5sNcawJQw6o6CnCRrvHGxWfDj23GHZZnQKn0MgMFo2yu6aR7heDjbpTmMosM4QhuC4z7jniPT"
headers = {"Authorization": TOKEN, "Accept": "application/json"}

lista_de_ids = [
    "273491403", "544340267", "366987777", "475685597", 
    "505769527", "505767847", "505786577", "505786857", 
    "505806137", "240785002"
]

# 4. FUNÇÃO DE INGESTÃO 
@st.cache_data(ttl=3600) 
def carregar_dados_ceic():
    lista_resultados = []
    df_historico_ipca = pd.DataFrame()
    
    for sid in lista_de_ids:
        # Metadados
        resp_meta = requests.get(f"https://api.ceicdata.com/v2/series/{sid}", headers=headers).json()
        item_meta = resp_meta.get("data", [{}])[0] if isinstance(resp_meta.get("data"), list) else resp_meta.get("data", {})
        nome_ind = item_meta.get("metadata", {}).get("name", f"ID {sid}")
        att_bruto = item_meta.get("metadata", {}).get("timepointsLastUpdateTime")
        
        # Dados
        resp_data = requests.get(f"https://api.ceicdata.com/v2/series/{sid}/data", headers=headers, params={"startDate": "2024-01-01"}).json()
        pontos = resp_data.get("data", [{}])[0].get("timePoints", []) if isinstance(resp_data.get("data"), list) else resp_data.get("data", {}).get("timePoints", [])
        
        if pontos:
            df_temp = pd.DataFrame(pontos)
            df_temp['date'] = pd.to_datetime(df_temp['date'])
            
            # =======================================================
            # A CORREÇÃO ESTÁ AQUI: 
            # Forçamos a tabela a se organizar da data mais antiga para a mais nova
            # =======================================================
            df_temp = df_temp.sort_values(by='date', ascending=True).reset_index(drop=True)
            
            # Agora temos 100% de certeza que a linha final (-1) é a ponta mais recente
            valor_bruto = df_temp.iloc[-1]['value']
            ultimo_valor = f"{valor_bruto:,.4f}" 
            
            # Salvando a série do IPCA para o gráfico
            if sid == "273491403":
                df_historico_ipca = df_temp[['date', 'value']].set_index('date')
        else:
            ultimo_valor = "N/A"

        # Cálculo de Latência
        if att_bruto and "T" in att_bruto:
            horario_sp = pd.to_datetime(att_bruto).tz_convert('America/Sao_Paulo')
            horario_oficial = horario_sp.replace(hour=9, minute=0, second=0, microsecond=0)
            atraso = (horario_sp - horario_oficial).total_seconds()
            
            if atraso < 0:
                latencia_str = "🟢 Adiantado"
            else:
                latencia_str = f"🔴 {int(atraso // 60)}m {int(atraso % 60)}s"
        else:
            latencia_str = "Desconhecida"
            
        lista_resultados.append({
            "Indicador": nome_ind,
            "Último Valor": ultimo_valor,
            "Latência API": latencia_str,
            "Atualização": horario_sp.strftime('%d/%m/%Y %H:%M') if 'horario_sp' in locals() else "-"
        })
        
    return pd.DataFrame(lista_resultados), df_historico_ipca

# 5. RENDERIZANDO A INTERFACE
with st.spinner("Conectando à API do CEIC..."):
    df_tabela, df_ipca = carregar_dados_ceic()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Auditoria de Ingestão e Latência")
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Evolução - IPCA: General")
    if not df_ipca.empty:
        st.line_chart(df_ipca)
    else:
        st.info("Gráfico não disponível.")
