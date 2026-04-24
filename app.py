# =============================================================================
# APP.PY - Interface Streamlit para Relatório Semanal de Qualidade
# =============================================================================
# Energimp - Equipe de Qualidade
# Execução: streamlit run app.py
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import sys
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Adicionar diretório atual ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend import (
    testar_conexao, pipeline_completo, carregar_dados_excel,
    processar_atividades, carregar_pcm, salvar_pcm,
    adicionar_atividade_pcm, remover_atividade_pcm, limpar_pcm,
    obter_semana_atual, obter_tipos_atividade,
    PARQUES_POR_REGIONAL, TODOS_PARQUES, CORES_REGIONAL,
    PARQUES_INFO, HAS_PSYCOPG2,
    calcular_cobertura_parques, calcular_cobertura_regional,
    comparar_pcm_executado,
)
from relatorio_pdf_corporativo import (
    gerar_relatorio_pdf,
    gerar_relatorio_completo_por_semana,
    gerar_relatorio_semana_anterior,
)
from planejamento_pcm import (
    ler_programacao_pcm, agrupar_atividades_pcm,
    carregar_tasks, salvar_tasks, criar_tasks_do_pcm,
    atualizar_task, obter_tasks_semana, obter_semanas_disponiveis,
    limpar_tasks_semana, adicionar_task_manual,
    salvar_historico, carregar_historico, obter_resumo_planejamento,
    MOTIVOS_NAO_CUMPRIMENTO, EQUIPES_QLW,
)

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Qualidade - Energimp",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A1628 0%, #162036 100%) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] label {
        color: #c7d2e0 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1) !important;
    }

    /* Header banner */
    .main-banner {
        background: linear-gradient(135deg, #0D1B3E 0%, #1a3a6e 100%);
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 28px;
        box-shadow: 0 4px 20px rgba(13, 27, 62, 0.15);
    }
    .main-banner h1 {
        color: white !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin: 0 0 4px !important;
        padding: 0 !important;
    }
    .main-banner p {
        color: #8ca3c4 !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
    }

    /* KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 28px;
    }
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 22px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border-top: 3px solid #0D1B3E;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
    }
    .kpi-card.cyan { border-top-color: #00ACC1; }
    .kpi-card.coral { border-top-color: #FF6B6B; }
    .kpi-card.green { border-top-color: #4CAF50; }
    .kpi-value {
        font-size: 2.4rem;
        font-weight: 700;
        color: #0D1B3E;
        line-height: 1.1;
        margin: 6px 0;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #7b8794;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-weight: 600;
    }
    .kpi-sub {
        font-size: 0.72rem;
        color: #00ACC1;
        margin-top: 4px;
        font-weight: 500;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-ok {
        background: rgba(76, 175, 80, 0.15);
        color: #2E7D32;
    }
    .status-err {
        background: rgba(255, 107, 107, 0.15);
        color: #C62828;
    }
    .status-warn {
        background: rgba(255, 152, 0, 0.15);
        color: #E65100;
    }

    /* Section headers */
    .section-title {
        color: #0D1B3E;
        font-size: 1.2rem;
        font-weight: 700;
        margin: 20px 0 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e8ecf1;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f0f2f6;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0D1B3E, #1a3a6e) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(13,27,62,0.3) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Week section styling */
    .week-header {
        background: linear-gradient(135deg, #f8f9fc, #eef1f6);
        padding: 12px 18px;
        border-radius: 10px;
        border-left: 4px solid;
        margin: 16px 0 10px;
    }
    .week-header.current { border-left-color: #00ACC1; }
    .week-header.previous { border-left-color: #1565C0; }
    .week-header h4 {
        margin: 0 !important;
        font-size: 1rem !important;
    }
    .week-header p {
        margin: 2px 0 0 !important;
        font-size: 0.82rem !important;
        color: #7b8794 !important;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================
if 'df_dados_completo' not in st.session_state:
    st.session_state.df_dados_completo = None
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False
if 'pcm_counter' not in st.session_state:
    st.session_state.pcm_counter = 0
if 'mensagem_status' not in st.session_state:
    st.session_state.mensagem_status = ""


# =============================================================================
# FUNÇÕES AUXILIARES DE UI
# =============================================================================
def render_kpi_cards(kpis):
    """Renderiza cards de KPI. kpis = [(label, value, css_class, sub_text), ...]"""
    cards_html = '<div class="kpi-grid">'
    for label, value, css_cls, sub in kpis:
        cards_html += f'''
        <div class="kpi-card {css_cls}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>'''
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)


def obter_label_semana(ano, semana_num):
    """Retorna label da semana no formato YYYY-SXX."""
    return f"{ano}-S{str(semana_num).zfill(2)}"


def obter_info_semana(ref_date, offset_weeks=0):
    """Retorna info de uma semana com offset relativo a ref_date."""
    target = ref_date + datetime.timedelta(weeks=offset_weeks)
    inicio = target - datetime.timedelta(days=target.weekday())
    fim = inicio + datetime.timedelta(days=6)
    semana_num = target.isocalendar()[1]
    ano = target.isocalendar()[0]
    return {
        'semana_num': semana_num,
        'ano': ano,
        'inicio': inicio,
        'fim': fim,
        'periodo': f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}",
        'label': obter_label_semana(ano, semana_num)
    }


def render_detalhe_semana(ativ_t, label_semana, titulo, periodo, css_class="current"):
    """Renderiza seção de detalhe de uma semana específica."""
    df_semana = ativ_t[ativ_t['ano_semana'] == label_semana] if not ativ_t.empty else pd.DataFrame()

    st.markdown(f'''
    <div class="week-header {css_class}">
        <h4>{titulo}</h4>
        <p>{periodo}</p>
    </div>
    ''', unsafe_allow_html=True)

    if not df_semana.empty:
        col_t1, col_t2 = st.columns([1, 2])
        with col_t1:
            st.markdown("**Resumo por Regional**")
            resumo = df_semana.groupby('grupo_equipe').agg(
                Atividades=('aerogerador', 'count'),
                Maquinas=('aerogerador', 'nunique'),
                Parques=('parque', 'nunique'),
            ).reset_index()
            resumo.columns = ['Regional', 'Atividades', 'Máquinas', 'Parques']
            st.dataframe(resumo, use_container_width=True, hide_index=True)

        with col_t2:
            st.markdown("**Turbinas Atendidas**")
            detalhe = df_semana.groupby(['grupo_equipe', 'aerogerador', 'parque']).agg(
                Tipo=('desc_esquema', lambda x: ' | '.join(sorted(x.unique()))),
            ).reset_index()
            detalhe.columns = ['Regional', 'Aerogerador', 'Parque', 'Tipo de Atividade']
            st.dataframe(detalhe, use_container_width=True, hide_index=True)
    else:
        st.caption(f"Sem atividades registradas para {label_semana}")


def filtrar_dados_por_periodo(df_completo, dt_ini, dt_fim):
    """Filtra os dados pelo período selecionado e reprocessa."""
    if df_completo is None or df_completo.empty:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df_completo.copy()
    df['data_inicio_exec'] = pd.to_datetime(df['data_inicio_exec'])
    mask = (df['data_inicio_exec'].dt.date >= dt_ini) & (df['data_inicio_exec'].dt.date <= dt_fim)
    df_filtrado = df[mask]

    if df_filtrado.empty:
        return df_filtrado, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    ativ_t, ativ_a, ativ_av = processar_atividades(df_filtrado)
    return df_filtrado, ativ_t, ativ_a, ativ_av


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    # Logo
    logo_path = os.path.join(BASE_DIR, 'logo_energimp.png')
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    else:
        st.markdown("""
        <div style="text-align:center; margin-bottom:8px;">
            <span style="font-size:1.6rem; font-weight:700; color:#00BCD4;">⚡ energimp</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Qualidade")

    # Indicador de ambiente
    if HAS_PSYCOPG2:
        st.markdown('<span class="status-badge status-ok">🖥️ Modo Local</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge" style="background:rgba(0,172,193,0.15);color:#00838F;">☁️ Modo Cloud</span>',
                    unsafe_allow_html=True)

    st.markdown("---")

    # Datas
    st.markdown("##### 📅 Período dos Dados")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Início", value=datetime.date(2026, 1, 1),
                                     format="DD/MM/YYYY", key="dt_ini")
    with col2:
        data_fim = st.date_input("Fim", value=datetime.date.today(),
                                  format="DD/MM/YYYY", key="dt_fim")

    st.markdown("---")

    # Botão Atualizar do banco (só quando psycopg2 disponível)
    if HAS_PSYCOPG2:
        if st.button("🔄 Atualizar Dados do EQM", type="primary", use_container_width=True):
            with st.spinner("Conectando ao banco EQM..."):
                df, ativ_t, ativ_a, msg = pipeline_completo(
                    pd.to_datetime(data_inicio), pd.to_datetime(data_fim)
                )
                if df is not None:
                    st.session_state.df_dados_completo = df
                    st.session_state.dados_carregados = True
                    st.session_state.mensagem_status = msg
                    st.success(msg)
                else:
                    st.session_state.mensagem_status = msg
                    st.error(msg)

    # Botão carregar do Excel local (sempre disponível)
    if st.button("📂 Carregar do Excel Local", use_container_width=True):
        df = carregar_dados_excel()
        if df is not None and not df.empty:
            st.session_state.df_dados_completo = df
            st.session_state.dados_carregados = True
            st.success(f"✅ {len(df)} registros carregados do Excel")
        else:
            st.warning("Excel não encontrado ou vazio")

    # Upload de Excel (especialmente útil no cloud)
    st.markdown("---")
    st.markdown("##### 📤 Upload de Dados")
    uploaded_file = st.file_uploader(
        "Enviar Excel (.xlsx)",
        type=["xlsx"],
        help="Envie o arquivo Resumo_Atividades_Qualidade_2026.xlsx"
    )
    if uploaded_file is not None:
        try:
            df_upload = pd.read_excel(uploaded_file)
            if not df_upload.empty:
                st.session_state.df_dados_completo = df_upload
                st.session_state.dados_carregados = True
                st.success(f"✅ {len(df_upload)} registros carregados via upload")
        except Exception as e:
            st.error(f"Erro ao ler Excel: {str(e)}")

    st.markdown("---")

    # Status
    sem_atual = obter_semana_atual()
    st.markdown(f"##### 📆 Semana Atual: **S{sem_atual['semana_num']}**")
    st.caption(sem_atual['periodo'])

    if st.session_state.dados_carregados:
        st.markdown('<span class="status-badge status-ok">✅ Dados carregados</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge status-warn">⏳ Sem dados</span>',
                    unsafe_allow_html=True)

    # Info PCM
    pcm = carregar_pcm()
    st.markdown(f"📝 **PCM:** {len(pcm)} atividades planejadas")


# =============================================================================
# CARREGAR DADOS AUTOMATICAMENTE (do Excel se existir)
# =============================================================================
if not st.session_state.dados_carregados:
    df = carregar_dados_excel()
    if df is not None and not df.empty:
        st.session_state.df_dados_completo = df
        st.session_state.dados_carregados = True


# =============================================================================
# FILTRAR DADOS PELO PERÍODO SELECIONADO (reativo às datas)
# =============================================================================
df_filtrado, ativ_t, ativ_a, ativ_av = filtrar_dados_por_periodo(
    st.session_state.df_dados_completo, data_inicio, data_fim
)


# =============================================================================
# BANNER PRINCIPAL
# =============================================================================
st.markdown("""
<div class="main-banner">
    <h1>⚡ Relatório Semanal de Qualidade</h1>
    <p>Acompanhamento de atividades da equipe de qualidade em aerogeradores</p>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Painel Principal", "📝 Planejamento PCM", "📋 Planejamento Semanal", "📥 Gerar Relatório"])


# =============================================================================
# Calcular semanas: anterior, atual, próxima
# =============================================================================
hoje = datetime.date.today()
sem_anterior = obter_info_semana(hoje, offset_weeks=-1)
sem_corrente = obter_info_semana(hoje, offset_weeks=0)
sem_proxima = obter_info_semana(hoje, offset_weeks=1)


# =============================================================================
# TAB 1: PAINEL PRINCIPAL
# =============================================================================
with tab1:
    if st.session_state.dados_carregados and not ativ_t.empty:
        total_ativ = len(ativ_t)
        total_maq = ativ_t['aerogerador'].nunique()
        total_parques = ativ_t['parque'].nunique()
        total_ferr = int(ativ_a['ferramentas_auditadas'].sum()) if ativ_a is not None and not ativ_a.empty else 0
        total_aval = int(ativ_av['qtd_avaliacoes'].sum()) if ativ_av is not None and not ativ_av.empty else 0
        semanas = sorted(ativ_t['ano_semana'].unique())

        # Cobertura global do período
        df_cob_reg = calcular_cobertura_regional(ativ_t)
        total_maq_universo = sum(v['qtd_maq'] for v in PARQUES_INFO.values())
        cobertura_geral = round(total_maq / total_maq_universo * 100, 1) if total_maq_universo else 0

        # ── Nota explicativa de Atividade ────────────────────────────────────
        st.markdown("""
        <div style="background:#f0f4ff;border-left:4px solid #0D1B3E;border-radius:10px;
                    padding:10px 16px;margin-bottom:16px;font-size:0.83rem;color:#3d4f6e;">
            <strong>📌 Definição de Atividade em Turbina:</strong>
            Combinação única de <em>Regional + Data + Aerogerador + Tipo de Serviço</em>.
            Uma mesma turbina pode gerar múltiplas atividades se recebeu tipos distintos de serviço.
            A coluna <em>OS Total</em> mostra a contagem bruta de Ordens de Serviço no EQM.
        </div>
        """, unsafe_allow_html=True)

        # KPIs — Linha 1
        render_kpi_cards([
            ("Atividades em Turbinas", total_ativ, "",
             f"{len(semanas)} sem. | 1 ativ = turbina+tipo+data"),
            ("Máquinas Distintas", total_maq, "cyan",
             f"{total_parques} parques | {cobertura_geral}% do universo"),
            ("Ferramentas Auditadas", total_ferr, "green", "Auditorias MPP6"),
            ("Avaliações de Equipe", total_aval, "coral",
             f"S{sem_corrente['semana_num']} | {sem_corrente['periodo']}"),
        ])

        # KPIs — Linha 2: Cobertura por Regional
        if not df_cob_reg.empty:
            st.markdown('<div class="section-title">🎯 Cobertura de Máquinas por Regional</div>',
                        unsafe_allow_html=True)
            kpis_cobertura = []
            for _, row in df_cob_reg.iterrows():
                kpis_cobertura.append((
                    f"Cobertura {row['Regional']}",
                    f"{row['Cobertura_%']}%",
                    "cyan" if row['Cobertura_%'] >= 80 else
                    "" if row['Cobertura_%'] >= 50 else "coral",
                    f"{row['Maq_Atendidas']} / {row['Maq_Total']} turbinas"
                ))
            render_kpi_cards(kpis_cobertura)

        # Gráficos
        st.markdown('<div class="section-title">📈 Evolução Semanal <span style="font-size:0.72rem;color:#7b8794;font-weight:400">(barras = nº de atividades por turbina+tipo; linha = média do período)</span></div>',
                    unsafe_allow_html=True)

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            pivot = ativ_t.pivot_table(
                index='ano_semana', columns='grupo_equipe',
                values='aerogerador', aggfunc='count', fill_value=0
            ).reindex(semanas, fill_value=0)

            media_geral = pivot.sum(axis=1).mean()

            fig, ax = plt.subplots(figsize=(8, 4))
            cores = [CORES_REGIONAL.get(c, '#9E9E9E') for c in pivot.columns]
            pivot.plot(kind='bar', stacked=True, ax=ax, color=cores,
                      edgecolor='white', linewidth=0.5, width=0.7)
            for i, sem in enumerate(pivot.index):
                total = pivot.loc[sem].sum()
                ax.annotate(f'{int(total)}', xy=(i, total), xytext=(0, 3),
                            textcoords="offset points", ha='center',
                            fontsize=8, fontweight='bold', color='#0D1B3E')
            # Linha de média
            ax.axhline(media_geral, color='#FF6B6B', linewidth=1.4,
                       linestyle='--', label=f'Média ({media_geral:.0f})', zorder=5)
            ax.set_title('Atividades por Semana\n(turbina+tipo)', fontweight='bold', color='#0D1B3E', fontsize=10)
            ax.set_xlabel('')
            ax.set_ylabel('Atividades')
            labels = [s.replace('-S', '\nS') for s in pivot.index]
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=0, fontsize=7)
            ax.legend(title='Regional', fontsize=7, title_fontsize=8)
            ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        with col_g2:
            # Máquinas distintas por semana (nunique) — complementa o gráfico de atividades
            pivot_maq = ativ_t.pivot_table(
                index='ano_semana', columns='grupo_equipe',
                values='aerogerador', aggfunc='nunique', fill_value=0
            ).reindex(semanas, fill_value=0)
            media_maq = pivot_maq.sum(axis=1).mean()

            fig2, ax2 = plt.subplots(figsize=(8, 4))
            for regional in pivot_maq.columns:
                cor = CORES_REGIONAL.get(regional, '#9E9E9E')
                ax2.plot(pivot_maq.index, pivot_maq[regional], marker='o', linewidth=2,
                        markersize=5, label=regional, color=cor)
                for x, y in zip(pivot_maq.index, pivot_maq[regional]):
                    if y > 0:
                        ax2.annotate(str(int(y)), (x, y), textcoords="offset points",
                                    xytext=(0, 7), ha='center', fontsize=7,
                                    fontweight='bold', color=cor)
            ax2.axhline(media_maq, color='#FF6B6B', linewidth=1.4,
                        linestyle='--', label=f'Média ({media_maq:.0f})', zorder=5)
            ax2.set_title('Turbinas Distintas por Semana\n(máquinas únicas atendidas)', fontweight='bold', color='#0D1B3E', fontsize=10)
            ax2.set_xlabel('')
            ax2.set_ylabel('Turbinas Distintas')
            ax2.legend(fontsize=7)
            labels2 = [s.replace('-S', '\nS') for s in pivot_maq.index]
            ax2.set_xticks(range(len(labels2)))
            ax2.set_xticklabels(labels2, rotation=0, fontsize=7)
            ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close()

        # ── Cobertura por Parque ────────────────────────────────────────────
        st.markdown('<div class="section-title">📊 Cobertura Detalhada por Parque</div>',
                    unsafe_allow_html=True)
        df_cob_pq = calcular_cobertura_parques(ativ_t)
        if not df_cob_pq.empty:
            col_cob1, col_cob2 = st.columns([2, 1])
            with col_cob1:
                # Gráfico de cobertura por parque
                fig_cob, ax_cob = plt.subplots(figsize=(9, max(3, len(df_cob_pq) * 0.38)))
                cores_cob = [
                    '#4CAF50' if v >= 80 else '#FF9800' if v >= 50 else '#F44336'
                    for v in df_cob_pq['Cobertura_%']
                ]
                bars = ax_cob.barh(
                    df_cob_pq['Parque'], df_cob_pq['Cobertura_%'],
                    color=cores_cob, edgecolor='white', height=0.55
                )
                ax_cob.axvline(100, color='#9E9E9E', linewidth=0.8, linestyle='--')
                for bar, row in zip(bars, df_cob_pq.itertuples()):
                    w = bar.get_width()
                    ax_cob.annotate(
                        f"{w:.0f}% ({row.Maq_Atendidas}/{row.Maq_Total})",
                        xy=(w, bar.get_y() + bar.get_height() / 2),
                        xytext=(4, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=7.5, fontweight='bold'
                    )
                ax_cob.set_xlim(0, 115)
                ax_cob.set_xlabel('Cobertura (%)', fontweight='bold')
                ax_cob.set_title('% Cobertura de Máquinas por Parque\n(verde ≥80%, amarelo ≥50%, vermelho <50%)',
                                 fontweight='bold', color='#0D1B3E', fontsize=10)
                plt.tight_layout()
                st.pyplot(fig_cob)
                plt.close()
            with col_cob2:
                st.dataframe(
                    df_cob_pq[['Parque', 'Regional', 'Maq_Atendidas', 'Maq_Total', 'Cobertura_%']]
                    .rename(columns={'Maq_Atendidas': 'Atendidas', 'Maq_Total': 'Total',
                                    'Cobertura_%': 'Cobertura%'}),
                    use_container_width=True, hide_index=True
                )

        # ===== SEMANA ANTERIOR =====
        st.markdown('<div class="section-title">📋 Detalhe Semanal</div>',
                    unsafe_allow_html=True)

        render_detalhe_semana(
            ativ_t, sem_anterior['label'],
            f"⏮️ Semana Anterior — S{sem_anterior['semana_num']}",
            sem_anterior['periodo'],
            css_class="previous"
        )

        # ===== SEMANA ATUAL =====
        render_detalhe_semana(
            ativ_t, sem_corrente['label'],
            f"📌 Semana Atual — S{sem_corrente['semana_num']}",
            sem_corrente['periodo'],
            css_class="current"
        )

    else:
        st.info("👈 Clique em **Atualizar Dados do EQM** ou **Carregar do Excel Local** na barra lateral para começar.")
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color: #7b8794;">
            <div style="font-size: 4rem; margin-bottom: 16px;">📊</div>
            <div style="font-size: 1.1rem; font-weight: 600;">Nenhum dado carregado</div>
            <div style="font-size: 0.9rem; margin-top: 8px;">
                Use os botões na barra lateral para carregar os dados do banco EQM ou do Excel local.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB 2: PLANEJAMENTO PCM
# =============================================================================
with tab2:
    st.markdown('<div class="section-title">📝 Atividades Planejadas - PCM</div>',
                unsafe_allow_html=True)
    st.caption(f"Semana {sem_corrente['semana_num']} — {sem_corrente['periodo']} "
               f"| Planejamento × Executado: compara parque + semana + tipo de atividade")

    # Formulário
    with st.expander("➕ Adicionar Atividade Planejada", expanded=True):
        with st.form("form_pcm", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                regional = st.selectbox("Regional", ["AGD", "BJS", "CE"])
                parques_regional = PARQUES_POR_REGIONAL.get(regional, TODOS_PARQUES)
                parque = st.selectbox("Parque", parques_regional)

            with col2:
                aerogerador = st.text_input("Aerogerador", placeholder="Ex: CAJ-11")
                tipos = obter_tipos_atividade()
                tipo = st.selectbox("Tipo de Atividade", tipos)

            with col3:
                data_prevista = st.date_input("Data Prevista", value=datetime.date.today(),
                                              format="DD/MM/YYYY")
                responsavel = st.text_input("Responsável", placeholder="Nome do técnico")

            observacoes = st.text_input("Observações", placeholder="Informações adicionais...")

            submitted = st.form_submit_button("✅ Adicionar Atividade", type="primary",
                                               use_container_width=True)
            if submitted:
                if not aerogerador.strip():
                    st.warning("Preencha o campo Aerogerador")
                else:
                    adicionar_atividade_pcm(
                        regional, parque, aerogerador.strip().upper(),
                        tipo, data_prevista, responsavel, observacoes
                    )
                    st.success(f"✅ Atividade adicionada: {aerogerador.upper()} - {tipo}")
                    st.session_state.pcm_counter += 1
                    st.rerun()

    # Tabela de atividades planejadas
    pcm = carregar_pcm()
    if pcm:
        st.markdown(f"**{len(pcm)} atividades planejadas:**")
        df_pcm = pd.DataFrame(pcm)
        cols_show = ['regional', 'parque', 'aerogerador', 'tipo_atividade',
                     'data_prevista', 'responsavel', 'observacoes']
        cols_exist = [c for c in cols_show if c in df_pcm.columns]
        df_display = df_pcm[cols_exist].copy()
        df_display.columns = [c.replace('_', ' ').title() for c in cols_exist]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Botões de ação
        col_a1, col_a2, col_a3 = st.columns([1, 1, 2])
        with col_a1:
            idx_remover = st.number_input("Linha para remover", min_value=1,
                                          max_value=len(pcm), value=1, step=1)
            if st.button("🗑️ Remover Linha", use_container_width=True):
                remover_atividade_pcm(idx_remover - 1)
                st.rerun()
        with col_a2:
            if st.button("🧹 Limpar Todas", use_container_width=True):
                limpar_pcm()
                st.rerun()

        # ── Comparação PCM × Executado ────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="section-title">🔁 Planejado × Executado</div>',
                    unsafe_allow_html=True)
        st.caption("Critério: mesmo parque + mesma semana (pela data prevista) + tipo de atividade similar")

        if st.session_state.dados_carregados and ativ_t is not None and not ativ_t.empty:
            df_pcm_exec = comparar_pcm_executado(pcm, ativ_t)
            if not df_pcm_exec.empty:
                n_exec = (df_pcm_exec['Executado?'] == '✅ Sim').sum()
                n_total = len(df_pcm_exec)
                aderencia = round(n_exec / n_total * 100, 1) if n_total else 0

                col_ka, col_kb = st.columns([1, 3])
                with col_ka:
                    cor_ader = "#4CAF50" if aderencia >= 80 else "#FF9800" if aderencia >= 50 else "#F44336"
                    st.markdown(f"""
                    <div style="background:white;border-radius:14px;padding:20px;
                                box-shadow:0 2px 12px rgba(0,0,0,0.06);
                                border-top:3px solid {cor_ader};text-align:center;">
                        <div style="font-size:0.75rem;color:#7b8794;font-weight:600;
                                    text-transform:uppercase;letter-spacing:0.5px;">
                            Aderência PCM
                        </div>
                        <div style="font-size:2.4rem;font-weight:700;color:{cor_ader};
                                    line-height:1.2;margin:8px 0;">
                            {aderencia:.0f}%
                        </div>
                        <div style="font-size:0.78rem;color:#546e7a;">
                            {n_exec} de {n_total} executadas
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_kb:
                    st.dataframe(df_pcm_exec, use_container_width=True, hide_index=True)
            else:
                st.info("Não foi possível cruzar os dados. Verifique se as datas previstas estão dentro do período carregado.")
        else:
            st.caption("Carregue os dados do EQM ou Excel para ver o comparativo.")

# =============================================================================
# TAB 3: PLANEJAMENTO SEMANAL (Atividades PCM)
# =============================================================================
with tab3:
    st.markdown('<div class="section-title">📋 Planejamento Semanal — Atividades via PCM</div>',
                unsafe_allow_html=True)
    st.caption("Leitura automática dos arquivos de programação PCM da pasta Atividades_PCM, "
               "filtrado para equipes QLW (CE, BJS, AGD).")

    # ── Sub-tabs do Planejamento ─────────────────────────────────────────
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "📥 Importar Programação", "✅ Acompanhamento Semanal", "📊 Relatório / Histórico"
    ])

    # ===== SUB-TAB 1: IMPORTAR PROGRAMAÇÃO =====
    with sub_t1:
        st.markdown("#### 📥 Importar Atividades da Programação PCM")
        st.markdown("""
        <div style="background:#f0f4ff;border-left:4px solid #0D1B3E;border-radius:10px;
                    padding:10px 16px;margin-bottom:16px;font-size:0.83rem;color:#3d4f6e;">
            <strong>📌 Como funciona:</strong> O sistema lê os 3 arquivos Excel da pasta
            <code>Atividades_PCM</code>, busca a aba "Base de Envio" ou "Programação",
            e filtra as equipes QLW-CE, QLW-BJS e QLW-AGD.
        </div>
        """, unsafe_allow_html=True)

        col_imp1, col_imp2 = st.columns([2, 1])
        with col_imp1:
            if st.button("🔄 Ler Programação PCM", type="primary", use_container_width=True,
                         key="btn_ler_pcm_prog"):
                with st.spinner("Lendo arquivos de programação..."):
                    df_prog = ler_programacao_pcm()
                    if not df_prog.empty:
                        st.session_state['df_prog_pcm'] = df_prog
                        st.session_state['df_prog_agrupado'] = agrupar_atividades_pcm(df_prog)
                        st.success(f"✅ {len(df_prog)} registros QLW encontrados "
                                   f"({len(st.session_state['df_prog_agrupado'])} atividades agrupadas)")
                    else:
                        st.warning("⚠️ Nenhuma atividade QLW encontrada nos arquivos.")

        # Mostrar dados importados
        if 'df_prog_pcm' in st.session_state and not st.session_state['df_prog_pcm'].empty:
            df_prog = st.session_state['df_prog_pcm']
            df_agr = st.session_state.get('df_prog_agrupado', pd.DataFrame())

            st.markdown("---")
            st.markdown("##### 📋 Atividades Encontradas (Detalhado)")
            cols_show_prog = ['regional', 'equipe', 'aerogerador', 'complemento',
                              'esquema', 'familia', 'ativo', 'responsavel', 'semana']
            cols_exist_prog = [c for c in cols_show_prog if c in df_prog.columns]
            df_show = df_prog[cols_exist_prog].copy()
            df_show.columns = [c.replace('_', ' ').title() for c in cols_exist_prog]
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            if not df_agr.empty:
                st.markdown("##### 📊 Atividades Agrupadas (por Atividade)")
                cols_agr = ['regional', 'equipe', 'aerogerador', 'complemento',
                            'esquema', 'familia', 'qtd_os']
                cols_agr_exist = [c for c in cols_agr if c in df_agr.columns]
                df_agr_show = df_agr[cols_agr_exist].copy()
                df_agr_show.columns = [c.replace('_', ' ').title() for c in cols_agr_exist]
                st.dataframe(df_agr_show, use_container_width=True, hide_index=True)

            # Botão para criar tasks
            st.markdown("---")
            col_task1, col_task2 = st.columns([2, 1])
            with col_task1:
                semana_import = st.text_input(
                    "Semana para importação",
                    value=f"S{sem_proxima['semana_num']}",
                    help="Identificador da semana (ex: S17, S18)",
                    key="semana_import_input"
                )
            with col_task2:
                sobrescrever = st.checkbox("Sobrescrever tasks da semana", value=False,
                                          key="chk_sobrescrever")

            if st.button("📌 Criar Tasks de Acompanhamento", type="primary",
                         use_container_width=True, key="btn_criar_tasks"):
                tasks = criar_tasks_do_pcm(df_prog, semana_import, sobrescrever=sobrescrever)
                salvar_historico(tasks)
                st.success(f"✅ {len(df_prog)} tasks criadas para {semana_import}!")
                st.rerun()

        # ── Adicionar Atividade Manual ────────────────────────────────────
        st.markdown("---")
        with st.expander("➕ Adicionar Atividade Planejada Manualmente"):
            with st.form("form_add_plan_manual", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    m_regional = st.selectbox("Regional", ["AGD", "BJS", "CE"],
                                             key="m_reg")
                    m_equipe = st.selectbox("Equipe", EQUIPES_QLW, key="m_eq")
                with c2:
                    m_aero = st.text_input("Aerogerador", placeholder="Ex: SAL-17",
                                          key="m_aero")
                    m_comp = st.text_input("Complemento", placeholder="Ex: SAL 17-C2",
                                          key="m_comp")
                with c3:
                    m_ativ = st.text_input("Atividade", placeholder="Ex: INSPEÇÃO PREVENTIVA",
                                          key="m_ativ")
                    m_familia = st.selectbox("Família", [
                        'Gerador', 'Nacelle', 'Torre WTG', 'Conversor',
                        'Sistema Pitch', 'Aerogerador', 'Outro'
                    ], key="m_fam")
                m_resp = st.text_input("Responsável", key="m_resp")
                m_sem = st.text_input("Semana", value=f"S{sem_proxima['semana_num']}",
                                     key="m_sem")

                if st.form_submit_button("✅ Adicionar", type="primary",
                                         use_container_width=True):
                    if m_aero.strip() and m_ativ.strip():
                        adicionar_task_manual(
                            m_sem, m_regional, m_equipe, m_aero.strip().upper(),
                            m_comp, m_ativ.strip().upper(), m_familia, m_resp
                        )
                        salvar_historico()
                        st.success(f"✅ Atividade manual adicionada: {m_aero.upper()}")
                        st.rerun()
                    else:
                        st.warning("Preencha Aerogerador e Atividade.")

    # ===== SUB-TAB 2: ACOMPANHAMENTO SEMANAL =====
    with sub_t2:
        st.markdown("#### ✅ Acompanhamento de Tarefas")

        semanas_disp = obter_semanas_disponiveis()
        if not semanas_disp:
            st.info("Nenhuma task criada ainda. Importe a programação PCM na aba anterior.")
        else:
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                semana_sel = st.selectbox("Selecione a Semana", semanas_disp,
                                         index=len(semanas_disp)-1,
                                         key="sel_semana_acomp")
            with col_sel2:
                st.markdown("")
                st.markdown("")
                retroativo = st.checkbox("🔙 Modo retroativo", value=False,
                                        help="Permite atualizar semanas anteriores",
                                        key="chk_retroativo")

            tasks_sem = obter_tasks_semana(semana_sel)
            if tasks_sem:
                resumo = obter_resumo_planejamento(semana_sel)

                # KPIs do planejamento
                cor_ader = ("#4CAF50" if resumo['aderencia'] >= 80
                           else "#FF9800" if resumo['aderencia'] >= 50
                           else "#F44336")
                st.markdown(f"""
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Total Atividades</div>
                        <div class="kpi-value">{resumo['total']}</div>
                        <div class="kpi-sub">Semana {semana_sel}</div>
                    </div>
                    <div class="kpi-card green">
                        <div class="kpi-label">Concluídas</div>
                        <div class="kpi-value">{resumo['concluidas']}</div>
                        <div class="kpi-sub">✅ Executadas</div>
                    </div>
                    <div class="kpi-card coral">
                        <div class="kpi-label">Pendentes</div>
                        <div class="kpi-value">{resumo['pendentes']}</div>
                        <div class="kpi-sub">⏳ Aguardando</div>
                    </div>
                    <div class="kpi-card" style="border-top-color:{cor_ader}">
                        <div class="kpi-label">Aderência</div>
                        <div class="kpi-value" style="color:{cor_ader}">{resumo['aderencia']}%</div>
                        <div class="kpi-sub">Planejado × Executado</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Formulário de atualização das tasks
                st.markdown("---")
                st.markdown("##### 📝 Atualizar Status das Atividades")
                st.caption("Marque as atividades concluídas e adicione observações quando necessário.")

                with st.form("form_update_tasks", clear_on_submit=False):
                    updates = []
                    for i, task in enumerate(tasks_sem):
                        with st.container():
                            emoji = "✅" if task['concluido'] else "⬜"
                            label_task = (f"{emoji} **{task['aerogerador']}** — "
                                         f"{task['atividade'][:50]} | "
                                         f"{task.get('familia', '')} | "
                                         f"Regional: {task['regional']}")
                            st.markdown(label_task)

                            c1, c2, c3 = st.columns([1, 2, 2])
                            with c1:
                                concluido = st.checkbox(
                                    "Concluído", value=task['concluido'],
                                    key=f"chk_{task['id']}"
                                )
                            with c2:
                                motivo = st.selectbox(
                                    "Motivo (se não concluído)",
                                    [''] + MOTIVOS_NAO_CUMPRIMENTO,
                                    index=([''] + MOTIVOS_NAO_CUMPRIMENTO).index(
                                        task['motivo_nao_cumprimento']
                                    ) if task['motivo_nao_cumprimento'] in MOTIVOS_NAO_CUMPRIMENTO else 0,
                                    key=f"mot_{task['id']}"
                                )
                            with c3:
                                obs = st.text_input(
                                    "Observações",
                                    value=task.get('observacoes', ''),
                                    key=f"obs_{task['id']}"
                                )
                            updates.append({
                                'task_id': task['id'],
                                'concluido': concluido,
                                'motivo': motivo,
                                'observacoes': obs,
                            })
                            st.markdown("<hr style='margin:4px 0;border-color:#eee'>",
                                       unsafe_allow_html=True)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        salvar_btn = st.form_submit_button(
                            "💾 Salvar Alterações", type="primary",
                            use_container_width=True
                        )
                    with col_btn2:
                        pass

                    if salvar_btn:
                        from planejamento_pcm import atualizar_tasks_em_lote
                        atualizar_tasks_em_lote(updates)
                        salvar_historico()
                        st.success("✅ Alterações salvas e histórico atualizado!")
                        st.rerun()

                # Botão limpar semana
                with st.expander("⚠️ Ações Avançadas"):
                    if st.button(f"🗑️ Limpar tasks da {semana_sel}",
                                key="btn_limpar_sem"):
                        limpar_tasks_semana(semana_sel)
                        salvar_historico()
                        st.warning(f"Tasks da {semana_sel} removidas.")
                        st.rerun()

    # ===== SUB-TAB 3: RELATÓRIO / HISTÓRICO =====
    with sub_t3:
        st.markdown("#### 📊 Relatório de Planejamento")

        semanas_hist = obter_semanas_disponiveis()
        if semanas_hist:
            sem_rel = st.selectbox("Semana", semanas_hist,
                                  index=len(semanas_hist)-1,
                                  key="sel_sem_relatorio")
            resumo_rel = obter_resumo_planejamento(sem_rel)
            tasks_rel = obter_tasks_semana(sem_rel)

            if tasks_rel:
                # Tabela resumo
                df_rel = pd.DataFrame(tasks_rel)
                cols_rel = ['regional', 'equipe', 'aerogerador', 'atividade',
                           'familia', 'concluido', 'motivo_nao_cumprimento', 'observacoes']
                cols_rel = [c for c in cols_rel if c in df_rel.columns]
                df_rel_show = df_rel[cols_rel].copy()
                if 'concluido' in df_rel_show.columns:
                    df_rel_show['concluido'] = df_rel_show['concluido'].map(
                        {True: '✅ Sim', False: '❌ Não'}
                    )
                df_rel_show.columns = [c.replace('_', ' ').title() for c in cols_rel]
                st.dataframe(df_rel_show, use_container_width=True, hide_index=True)

                # Gráfico de aderência por regional
                if resumo_rel['por_regional']:
                    st.markdown("##### 📈 Aderência por Regional")
                    regs = list(resumo_rel['por_regional'].keys())
                    aders = [resumo_rel['por_regional'][r]['aderencia'] for r in regs]

                    fig_ad, ax_ad = plt.subplots(figsize=(6, 3))
                    cores = ['#4CAF50' if a >= 80 else '#FF9800' if a >= 50
                             else '#F44336' for a in aders]
                    bars = ax_ad.bar(regs, aders, color=cores, edgecolor='white', width=0.5)
                    for bar, val in zip(bars, aders):
                        ax_ad.annotate(f'{val:.0f}%', xy=(bar.get_x() + bar.get_width()/2, val),
                                      xytext=(0, 5), textcoords='offset points',
                                      ha='center', fontweight='bold', fontsize=10)
                    ax_ad.set_ylim(0, 110)
                    ax_ad.set_ylabel('Aderência (%)')
                    ax_ad.set_title(f'Aderência ao Planejamento — {sem_rel}',
                                  fontweight='bold', color='#0D1B3E')
                    ax_ad.axhline(80, color='#4CAF50', linestyle='--', linewidth=0.8, alpha=0.5)
                    plt.tight_layout()
                    st.pyplot(fig_ad)
                    plt.close()

                # Motivos de não cumprimento
                if resumo_rel.get('motivos'):
                    st.markdown("##### 📋 Motivos de Não Cumprimento")
                    df_motivos = pd.DataFrame([
                        {'Motivo': k, 'Quantidade': v}
                        for k, v in resumo_rel['motivos'].items()
                    ]).sort_values('Quantidade', ascending=False)
                    st.dataframe(df_motivos, use_container_width=True, hide_index=True)

        # Histórico geral
        st.markdown("---")
        st.markdown("##### 📚 Histórico Completo")
        df_hist = carregar_historico()
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

            # Download do histórico
            buf = io.BytesIO()
            df_hist.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button(
                "📥 Download Histórico Excel",
                data=buf.getvalue(),
                file_name="historico_planejamento_pcm.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_hist_pcm"
            )
        else:
            st.info("Nenhum histórico disponível. Importe a programação e crie tasks.")


# =============================================================================
# TAB 4: GERAR RELATÓRIO
# =============================================================================
with tab4:
    st.markdown('<div class="section-title">📥 Gerar Relatório PDF</div>',
                unsafe_allow_html=True)

    if not st.session_state.dados_carregados:
        st.warning("⚠️ Carregue os dados primeiro (aba Painel ou botão na sidebar)")
    else:
        logo_path = os.path.join(BASE_DIR, 'logo_energimp.png')
        logo = logo_path if os.path.exists(logo_path) else None
        pcm_data = carregar_pcm()

        # ── OPÇÃO 1 ── Relatório Completo por Semana ──────────────────────────
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #f0f4ff, #e8f0fe);
                border-left: 5px solid #0D1B3E;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 18px;
            ">
                <div style="font-size:1.1rem; font-weight:700; color:#0D1B3E; margin-bottom:6px;">
                    📊 Relatório Completo — Todas as Semanas
                </div>
                <div style="font-size:0.87rem; color:#546e7a;">
                    Contém todas as atividades do período selecionado, organizadas semana a semana.
                    Inclui: capa, visão geral por semana (KPIs, tabelas por regional e turbina,
                    gráficos) e resumo acumulado ao final.
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_c1, col_c2 = st.columns([3, 1])
            with col_c2:
                gerar_completo = st.button(
                    "🚀 Gerar Completo",
                    type="primary",
                    use_container_width=True,
                    key="btn_relatorio_completo"
                )

            if gerar_completo:
                with st.spinner("Gerando Relatório Completo por Semana..."):
                    try:
                        pdf_path_completo = os.path.join(
                            BASE_DIR, 'Relatorio_Completo_Por_Semana.pdf'
                        )
                        gerar_relatorio_completo_por_semana(
                            ativ_t if ativ_t is not None else pd.DataFrame(),
                            ativ_a if ativ_a is not None else pd.DataFrame(),
                            output_path=pdf_path_completo,
                            logo_path=logo
                        )
                        st.success("✅ Relatório Completo gerado!")
                        with open(pdf_path_completo, 'rb') as f:
                            st.download_button(
                                label="📥 Download — Relatório Completo por Semana",
                                data=f.read(),
                                file_name=os.path.basename(pdf_path_completo),
                                mime='application/pdf',
                                use_container_width=True,
                                key="dl_relatorio_completo"
                            )
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar relatório completo: {str(e)}")
                        st.exception(e)

        st.markdown("---")

        # ── OPÇÃO 2 ── Relatório Semana Anterior ─────────────────────────────
        with st.container():
            # Mostrar qual é a semana anterior
            label_sem_ant = sem_anterior['label']
            periodo_sem_ant = sem_anterior['periodo']

            # Contagem rápida das atividades da semana anterior
            n_ativ_ant = 0
            if ativ_t is not None and not ativ_t.empty:
                n_ativ_ant = len(ativ_t[ativ_t['ano_semana'] == label_sem_ant])

            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #fff8f0, #fff3e0);
                border-left: 5px solid #E65100;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 18px;
            ">
                <div style="font-size:1.1rem; font-weight:700; color:#E65100; margin-bottom:6px;">
                    ⏮️ Relatório Semana Anterior — {label_sem_ant}
                </div>
                <div style="font-size:0.87rem; color:#546e7a;">
                    Período: <strong>{periodo_sem_ant}</strong> &nbsp;|&nbsp;
                    Atividades registradas: <strong>{n_ativ_ant}</strong><br>
                    Contém somente os dados da semana anterior: KPIs, gráficos de regional
                    e por tipo, tabela detalhada de turbinas e auditorias de ferramentas.
                    Inclui também o planejamento PCM para a próxima semana (se houver).
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_a1, col_a2 = st.columns([3, 1])
            with col_a1:
                inc_pcm_ant = st.checkbox(
                    "Incluir planejamento PCM (próxima semana)",
                    value=True,
                    key="pcm_semana_ant"
                )
            with col_a2:
                gerar_anterior = st.button(
                    "🚀 Gerar Semana Ant.",
                    type="primary",
                    use_container_width=True,
                    key="btn_relatorio_semana_ant"
                )

            if gerar_anterior:
                pcm_rel = pcm_data if inc_pcm_ant else []
                with st.spinner(f"Gerando Relatório Semana Anterior ({label_sem_ant})..."):
                    try:
                        pdf_path_ant = os.path.join(
                            BASE_DIR, 'Relatorio_Semana_Anterior.pdf'
                        )
                        gerar_relatorio_semana_anterior(
                            ativ_t if ativ_t is not None else pd.DataFrame(),
                            ativ_a if ativ_a is not None else pd.DataFrame(),
                            pcm_atividades=pcm_rel,
                            output_path=pdf_path_ant,
                            logo_path=logo
                        )
                        st.success(f"✅ Relatório da {label_sem_ant} gerado!")
                        with open(pdf_path_ant, 'rb') as f:
                            st.download_button(
                                label=f"📥 Download — Relatório {label_sem_ant}",
                                data=f.read(),
                                file_name=os.path.basename(pdf_path_ant),
                                mime='application/pdf',
                                use_container_width=True,
                                key="dl_relatorio_semana_ant"
                            )
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar relatório da semana anterior: {str(e)}")
                        st.exception(e)

        st.markdown("---")

        # ── OPÇÃO 3 ── Exportar Excel ─────────────────────────────────────────
        with st.expander("📊 Exportar Dados em Excel"):
            if st.button("📥 Gerar Excel Completo", use_container_width=True,
                         key="btn_excel"):
                with st.spinner("Gerando Excel..."):
                    try:
                        excel_path = os.path.join(BASE_DIR, 'Relatorio_Semanal_Completo.xlsx')
                        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                            if ativ_t is not None and not ativ_t.empty:
                                resumo = ativ_t.groupby(['ano_semana', 'periodo_semana']).agg(
                                    atividades=('aerogerador', 'count'),
                                    maquinas=('aerogerador', 'nunique'),
                                ).reset_index()
                                resumo.to_excel(writer, sheet_name='Resumo Semanal', index=False)

                                detalhe_base = ativ_t[['grupo_equipe', 'aerogerador', 'parque',
                                                  'desc_esquema', 'componentes',
                                                  'data_inicio_exec', 'ano_semana']].copy()
                                detalhe_base.columns = ['Regional', 'Aerogerador', 'Parque',
                                                   'Tipo', 'Componentes', 'Data', 'Semana']

                                # Expandir componentes: uma linha por componente
                                rows_exp = []
                                for _, row in detalhe_base.iterrows():
                                    comps = [c.strip() for c in str(row['Componentes']).split(',') if c.strip()]
                                    if not comps:
                                        comps = ['-']
                                    for comp in comps:
                                        r = row.copy()
                                        r['Componente'] = comp
                                        rows_exp.append(r)
                                detalhe_exp = pd.DataFrame(rows_exp)
                                detalhe_exp = detalhe_exp.drop(columns=['Componentes'])
                                cols_order = ['Semana', 'Data', 'Regional', 'Parque',
                                              'Aerogerador', 'Tipo', 'Componente']
                                detalhe_exp = detalhe_exp[[c for c in cols_order if c in detalhe_exp.columns]]
                                detalhe_exp.to_excel(writer, sheet_name='Atividades', index=False)

                            if pcm_data:
                                df_pcm_ex = pd.DataFrame(pcm_data)
                                df_pcm_ex.to_excel(writer, sheet_name='PCM Planejado', index=False)

                        st.success("✅ Excel gerado!")
                        with open(excel_path, 'rb') as f:
                            st.download_button(
                                label="📥 Download Excel",
                                data=f.read(),
                                file_name=os.path.basename(excel_path),
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                use_container_width=True,
                                key="dl_excel"
                            )
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar Excel: {str(e)}")
                        st.exception(e)
