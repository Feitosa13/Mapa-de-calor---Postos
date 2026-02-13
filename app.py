import pandas as pd
import numpy as np
import streamlit as st
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1IRlSnJIC2S_z4Mcx9iCnjUhvByDuOXASsGWbZGVhLhM/export?format=csv&gid=0"

st.set_page_config(page_title="Mapa de Calor - Postos", layout="wide")

@st.cache_data(ttl=60)  # atualiza a cada 60s
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    # Normaliza nomes (caso venham com espaços/acentos)
    df.columns = [c.strip().lower() for c in df.columns]
    return df

df = load_data(SHEET_CSV_URL)

# Esperado: etiqueta, lat, long, ocorrencias (ou ocorrências)
# Ajuste aqui se o nome da coluna for diferente no seu Sheets:
col_etiqueta = "etiqueta"
col_lat = "lat"
col_lon = "long"
col_occ = "ocorrencias" if "ocorrencias" in df.columns else "ocorrências"

# Converte coordenadas (caso venham como texto)
def to_float(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")

df[col_lat] = to_float(df[col_lat])
df[col_lon] = to_float(df[col_lon])
df[col_occ] = pd.to_numeric(df[col_occ], errors="coerce").fillna(0)

df = df.dropna(subset=[col_lat, col_lon])

st.title("Mapa de calor (satélite) — Postos x Ocorrências")

# Filtros
with st.sidebar:
    st.header("Filtros")
    min_occ, max_occ = int(df[col_occ].min()), int(df[col_occ].max())
    occ_range = st.slider("Faixa de ocorrências", min_occ, max_occ, (min_occ, max_occ))
    show_markers = st.checkbox("Mostrar marcadores clicáveis", True)
    heat_radius = st.slider("Raio do heatmap", 10, 80, 35)
    heat_blur = st.slider("Blur do heatmap", 10, 80, 25)

df_f = df[(df[col_occ] >= occ_range[0]) & (df[col_occ] <= occ_range[1])]

center = [float(df_f[col_lat].mean()), float(df_f[col_lon].mean())] if len(df_f) else [float(df[col_lat].mean()), float(df[col_lon].mean())]

m = folium.Map(location=center, zoom_start=13, control_scale=True, tiles=None)

# Satélite (Esri)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satélite",
    overlay=False,
    control=True,
).add_to(m)

# Rótulos (opcional)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Rótulos",
    overlay=True,
    control=True,
    opacity=0.9,
).add_to(m)

# Heatmap ponderado por ocorrências
heat = df_f[[col_lat, col_lon, col_occ]].values.tolist()
HeatMap(heat, radius=heat_radius, blur=heat_blur, max_zoom=17, name="Mapa de calor").add_to(m)

# Marcadores clicáveis
if show_markers:
    cluster = MarkerCluster(name="Postos (clicáveis)").add_to(m)
    for _, r in df_f.iterrows():
        etiqueta = r.get(col_etiqueta, "")
        occ = int(r[col_occ]) if pd.notna(r[col_occ]) else 0
        popup = folium.Popup(
            f"<b>Posto:</b> {etiqueta}<br><b>Ocorrências:</b> {occ}<br><b>Coords:</b> {r[col_lat]:.6f},{r[col_lon]:.6f}",
            max_width=350
        )
        folium.CircleMarker(
            location=[r[col_lat], r[col_lon]],
            radius=6,
            tooltip=f"{etiqueta} ({occ})",
            popup=popup,
            fill=True
        ).add_to(cluster)

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, use_container_width=True, height=700)

st.caption("Atualização automática: o app recarrega dados do Google Sheets (cache de 60s).")
