# =============================================================================
# RELATORIO SEMANAL DE ATIVIDADES DA EQUIPE DE QUALIDADE - PDF
# =============================================================================
# Le o arquivo Resumo_Atividades_Qualidade_2026.xlsx (gerado pelo notebook),
# agrupa as atividades semana a semana por Regional e Maquinas,
# gera tabelas e graficos e exporta tudo em PDF.
#
# IMPORTANTE: Auditorias de ferramentas (MPP6) sao segregadas por REGIONAL
# (e nao por turbina/parque), pois os codigos sao patrimonios de ferramentas.
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend nao interativo para gerar imagens
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.cm as cm
from fpdf import FPDF
from fpdf.fonts import FontFace
import os
import tempfile
from datetime import datetime
import unicodedata


def sanitize_latin1(text):
    """Converte texto para ser compativel com encoding latin-1 (FPDF built-in fonts)."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '\u2014': '-',   # em dash
        '\u2013': '-',   # en dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '*',   # bullet
        '\u00b2': '2',   # superscript 2
        '\u00b3': '3',   # superscript 3
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        result = []
        for ch in text:
            try:
                ch.encode('latin-1')
                result.append(ch)
            except UnicodeEncodeError:
                decomp = unicodedata.normalize('NFKD', ch)
                ascii_ch = decomp.encode('latin-1', errors='ignore').decode('latin-1')
                result.append(ascii_ch if ascii_ch else '?')
        return ''.join(result)


# =============================================================================
# CONFIGURACOES
# =============================================================================
ARQUIVO_DADOS = 'Resumo_Atividades_Qualidade_2026.xlsx'
ARQUIVO_PDF_SAIDA = 'Relatorio_Semanal_Atividades_Qualidade.pdf'
TEMP_DIR = tempfile.mkdtemp()

# Palavras-chave para identificar auditorias de ferramentas
AUDITORIA_KEYWORDS = ['AUDITORIA']

CORES_REGIONAL = {
    'AGD': '#1565C0',
    'CE':  '#E65100',
    'BJS': '#2E7D32',
    'OUTROS': '#757575'
}

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 9,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'axes.labelsize': 10,
    'figure.facecolor': '#FAFAFA',
    'axes.facecolor': '#FFFFFF',
    'axes.grid': True,
    'grid.alpha': 0.25,
    'grid.linestyle': '--',
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# =============================================================================
# 1. CARGA E PREPARACAO DOS DADOS
# =============================================================================
print("[*] Carregando dados...")
df = pd.read_excel(ARQUIVO_DADOS)

# Garantir tipos
df['data_inicio_exec'] = pd.to_datetime(df['data_inicio_exec'])
df['data_fim_exec'] = pd.to_datetime(df['data_fim_exec'])

# Derivar campos
df['parque'] = df['aerogerador'].str[:3]
df['ano'] = df['data_inicio_exec'].dt.year
df['semana_num'] = df['data_inicio_exec'].dt.isocalendar().week.astype(int)
df['ano_semana'] = df['data_inicio_exec'].dt.strftime('%Y') + '-S' + df['semana_num'].astype(str).str.zfill(2)

# Calcular inicio e fim da semana para exibicao no relatorio
df['inicio_semana'] = df['data_inicio_exec'] - pd.to_timedelta(
    df['data_inicio_exec'].dt.dayofweek, unit='D'
)
df['fim_semana'] = df['inicio_semana'] + pd.Timedelta(days=6)
df['periodo_semana'] = (
    df['inicio_semana'].dt.strftime('%d/%m') + ' a ' +
    df['fim_semana'].dt.strftime('%d/%m/%Y')
)

# Identificar tipo de registro
def eh_auditoria(desc):
    """Verifica se eh auditoria de ferramentas."""
    if pd.isna(desc):
        return False
    desc_upper = str(desc).upper()
    return any(kw in desc_upper for kw in AUDITORIA_KEYWORDS)

df['eh_auditoria'] = df['desc_esquema'].apply(eh_auditoria)
df['eh_avaliacao'] = df['desc_esquema'].str.upper().str.contains('AVALIA', na=False)

# === SEPARAR em 3 conjuntos: ===
# 1) Atividades em TURBINAS (nao eh auditoria nem avaliacao)
# 2) Auditorias de FERRAMENTAS (agrupadas por regional)
# 3) Avaliacoes de equipe (complementares, nao contam como atividade separada)

df_turbinas = df[~df['eh_auditoria'] & ~df['eh_avaliacao']].copy()
df_auditorias = df[df['eh_auditoria']].copy()

# --- ATIVIDADES EM TURBINAS ---
ativ_turbinas = df_turbinas.groupby(
    ['grupo_equipe', 'data_inicio_exec', 'aerogerador', 'parque',
     'desc_esquema', 'ano_semana', 'semana_num', 'periodo_semana']
).agg(
    qtd_os=('quantidade', 'sum'),
    componentes=('desc_especie', lambda x: ', '.join(sorted(x.unique())))
).reset_index()

# --- AUDITORIAS DE FERRAMENTAS (agrupadas por regional, nao por maquina) ---
ativ_auditorias = df_auditorias.groupby(
    ['grupo_equipe', 'ano_semana', 'semana_num', 'periodo_semana']
).agg(
    ferramentas_auditadas=('aerogerador', 'nunique'),
    qtd_os=('quantidade', 'sum'),
    desc_esquema=('desc_esquema', 'first')
).reset_index()

# Combinacao para graficos gerais (com campo tipo para diferenciar)
ativ_turbinas['tipo_registro'] = 'TURBINA'
# Para graficos que mostram tudo junto, criamos contagem unificada
# Mas nos detalhes, tratamos separadamente

# Ordenar por semana
semanas_ordenadas = sorted(set(
    list(ativ_turbinas['ano_semana'].unique()) +
    list(ativ_auditorias['ano_semana'].unique())
))

print(f"[OK] {len(ativ_turbinas)} atividades em turbinas + "
      f"{len(ativ_auditorias)} registros de auditoria de ferramentas")
print(f"     em {len(semanas_ordenadas)} semanas")

# =============================================================================
# 2. CONSTRUCAO DAS TABELAS SEMANAIS
# =============================================================================

def tabela_semanal_regional_turbinas(semana):
    """Retorna DataFrame resumo de atividades em TURBINAS de uma semana, por regional."""
    df_sem = ativ_turbinas[ativ_turbinas['ano_semana'] == semana]
    if df_sem.empty:
        return pd.DataFrame()

    resumo = df_sem.groupby('grupo_equipe').agg(
        atividades=('aerogerador', 'count'),
        maquinas_distintas=('aerogerador', 'nunique'),
        parques=('parque', 'nunique'),
        tipos=('desc_esquema', 'nunique'),
        os_total=('qtd_os', 'sum')
    ).reset_index()

    resumo.columns = ['Regional', 'Atividades', 'Maq. Distintas',
                       'Parques', 'Tipos', 'OS Total']
    resumo = resumo.sort_values('Atividades', ascending=False)
    return resumo


def tabela_semanal_maquinas(semana):
    """Retorna DataFrame com detalhe das maquinas (TURBINAS) por semana."""
    df_sem = ativ_turbinas[ativ_turbinas['ano_semana'] == semana]
    if df_sem.empty:
        return pd.DataFrame()

    detalhe = df_sem.groupby(['grupo_equipe', 'aerogerador', 'parque']).agg(
        tipo_atividade=('desc_esquema', lambda x: ' | '.join(sorted(x.unique()))),
        qtd_atividades=('desc_esquema', 'count'),
        componentes=('componentes', lambda x: ', '.join(sorted(set(', '.join(x).split(', ')))))
    ).reset_index()

    detalhe.columns = ['Regional', 'Aerogerador', 'Parque',
                       'Tipo de Atividade', 'Qtd Ativ.', 'Componentes']
    detalhe = detalhe.sort_values(['Regional', 'Parque', 'Aerogerador'])
    return detalhe


def tabela_semanal_auditorias(semana):
    """Retorna DataFrame resumo de AUDITORIAS DE FERRAMENTAS na semana, por regional."""
    df_sem = ativ_auditorias[ativ_auditorias['ano_semana'] == semana]
    if df_sem.empty:
        return pd.DataFrame()

    resumo = df_sem[['grupo_equipe', 'ferramentas_auditadas', 'qtd_os']].copy()
    resumo.columns = ['Regional', 'Ferramentas Auditadas', 'Total OS']
    resumo = resumo.sort_values('Ferramentas Auditadas', ascending=False)
    return resumo


# =============================================================================
# 3. GERACAO DE GRAFICOS
# =============================================================================

def gerar_grafico_barras_semanal():
    """Grafico de barras: atividades em TURBINAS por semana, empilhado por regional."""
    pivot = ativ_turbinas.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='aerogerador', aggfunc='count', fill_value=0
    )
    pivot = pivot.reindex(semanas_ordenadas, fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5.5))

    cores = [CORES_REGIONAL.get(c, '#9E9E9E') for c in pivot.columns]
    pivot.plot(kind='bar', stacked=True, ax=ax, color=cores,
               edgecolor='white', linewidth=0.6, width=0.7)

    for i, semana in enumerate(pivot.index):
        total = pivot.loc[semana].sum()
        ax.annotate(f'{int(total)}', xy=(i, total),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold',
                    color='#333333')

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Quantidade de Atividades', fontweight='bold')
    ax.set_title('Atividades em Turbinas - Semanais por Regional', fontsize=13, fontweight='bold', pad=10)
    ax.legend(title='Regional', bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)

    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)

    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(TEMP_DIR, 'grafico_semanal_barras.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    return path


def gerar_grafico_evolucao_regional():
    """Grafico de linhas: evolucao semanal por regional (TURBINAS)."""
    pivot = ativ_turbinas.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='aerogerador', aggfunc='count', fill_value=0
    )
    pivot = pivot.reindex(semanas_ordenadas, fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5))

    for regional in pivot.columns:
        cor = CORES_REGIONAL.get(regional, '#9E9E9E')
        ax.plot(pivot.index, pivot[regional], marker='o', linewidth=2.5,
                markersize=6, label=regional, color=cor, zorder=3)
        for x, y in zip(pivot.index, pivot[regional]):
            if y > 0:
                ax.annotate(str(int(y)), (x, y),
                            textcoords="offset points", xytext=(0, 8),
                            ha='center', fontsize=7.5, fontweight='bold', color=cor)

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Quantidade de Atividades', fontweight='bold')
    ax.set_title('Evolucao Semanal - Atividades em Turbinas por Regional', fontsize=13, fontweight='bold', pad=10)
    ax.legend(fontsize=9, loc='upper left')

    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(TEMP_DIR, 'grafico_evolucao_regional.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    return path


def gerar_grafico_tipo_por_semana():
    """Grafico de barras empilhadas: tipo de atividade em TURBINAS por semana."""
    pivot = ativ_turbinas.pivot_table(
        index='ano_semana', columns='desc_esquema',
        values='aerogerador', aggfunc='count', fill_value=0
    )
    pivot = pivot.reindex(semanas_ordenadas, fill_value=0)

    tipos_sorted = sorted(pivot.columns)
    cmap_obj = plt.colormaps.get_cmap('Set2')
    cores_tipo = {t: cmap_obj(i / max(len(tipos_sorted)-1, 1)) for i, t in enumerate(tipos_sorted)}

    fig, ax = plt.subplots(figsize=(14, 6))

    cores = [cores_tipo.get(c, '#78909C') for c in pivot.columns]
    pivot.plot(kind='bar', stacked=True, ax=ax, color=cores,
               edgecolor='white', linewidth=0.5, width=0.7)

    for i, semana in enumerate(pivot.index):
        total = pivot.loc[semana].sum()
        ax.annotate(f'{int(total)}', xy=(i, total),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Quantidade de Atividades', fontweight='bold')
    ax.set_title('Atividades em Turbinas - Semanais por Tipo', fontsize=13, fontweight='bold', pad=10)
    ax.legend(title='Tipo', bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=6.5)

    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(TEMP_DIR, 'grafico_tipo_semana.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    return path


def gerar_grafico_auditorias_semanal():
    """Grafico de barras: auditorias de ferramentas por semana, empilhado por regional."""
    if ativ_auditorias.empty:
        return None

    pivot = ativ_auditorias.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='ferramentas_auditadas', aggfunc='sum', fill_value=0
    )
    pivot = pivot.reindex(semanas_ordenadas, fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5))

    cores = [CORES_REGIONAL.get(c, '#9E9E9E') for c in pivot.columns]
    pivot.plot(kind='bar', stacked=True, ax=ax, color=cores,
               edgecolor='white', linewidth=0.6, width=0.7)

    for i, semana in enumerate(pivot.index):
        total = pivot.loc[semana].sum()
        if total > 0:
            ax.annotate(f'{int(total)}', xy=(i, total),
                        xytext=(0, 4), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold',
                        color='#333333')

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Ferramentas Auditadas', fontweight='bold')
    ax.set_title('Auditorias de Ferramentas (MPP6) - Semanais por Regional',
                 fontsize=13, fontweight='bold', pad=10)
    ax.legend(title='Regional', bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)

    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(TEMP_DIR, 'grafico_auditorias_semanal.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    return path


def gerar_grafico_maquinas_por_semana(semana):
    """Grafico de barras horizontais: maquinas (TURBINAS) atendidas na semana."""
    df_sem = ativ_turbinas[ativ_turbinas['ano_semana'] == semana]
    if df_sem.empty:
        return None

    maq_count = df_sem.groupby(['parque', 'aerogerador']).size().reset_index(name='atividades')
    maq_count = maq_count.sort_values(['parque', 'aerogerador'])

    if len(maq_count) > 30:
        # Se muitas maquinas, agrupa por parque
        parque_count = df_sem.groupby('parque')['aerogerador'].count().sort_values()
        fig, ax = plt.subplots(figsize=(10, max(3, len(parque_count)*0.5)))
        cores = ['#1565C0'] * len(parque_count)
        bars = ax.barh(parque_count.index, parque_count.values, color=cores,
                       edgecolor='white', height=0.5)
        for bar in bars:
            w = bar.get_width()
            ax.annotate(f'{int(w)}', xy=(w, bar.get_y() + bar.get_height()/2),
                        xytext=(4, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=8, fontweight='bold')
        ax.set_xlabel('Atividades')
        ax.set_title(f'Atividades por Parque - {semana}', fontsize=11, fontweight='bold')
    else:
        fig, ax = plt.subplots(figsize=(10, max(3, len(maq_count)*0.35)))
        cores = [CORES_REGIONAL.get(
            df_sem[df_sem['aerogerador'] == m]['grupo_equipe'].iloc[0], '#9E9E9E'
        ) for m in maq_count['aerogerador']]
        bars = ax.barh(maq_count['aerogerador'], maq_count['atividades'],
                       color=cores, edgecolor='white', height=0.5)
        for bar in bars:
            w = bar.get_width()
            ax.annotate(f'{int(w)}', xy=(w, bar.get_y() + bar.get_height()/2),
                        xytext=(4, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=8, fontweight='bold')
        ax.set_xlabel('Atividades')
        ax.set_title(f'Turbinas Atendidas - {semana}', fontsize=11, fontweight='bold')

    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(TEMP_DIR, f'grafico_maquinas_{semana}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    return path


# =============================================================================
# 4. CLASSE PDF CUSTOMIZADA
# =============================================================================

class RelatorioPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, sanitize_latin1('Relatorio Semanal de Atividades - Equipe de Qualidade'), align='L')
        self.set_font('Helvetica', '', 8)
        self.cell(0, 6, f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='R', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(21, 101, 192)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, sanitize_latin1(f'Pagina {self.page_no()}/{{nb}}'), align='C')

    def titulo_secao(self, texto, nivel=1):
        if nivel == 1:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(21, 101, 192)
        elif nivel == 2:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(50, 50, 50)
        else:
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(80, 80, 80)
        self.cell(0, 8, sanitize_latin1(texto), new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def adicionar_tabela(self, df, col_widths=None, font_size=7):
        """Renderiza um DataFrame como tabela estilizada."""
        if df.empty:
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 6, 'Sem dados para esta semana.', new_x='LMARGIN', new_y='NEXT')
            return

        n_cols = len(df.columns)

        if col_widths is None:
            available = self.w - 20
            col_widths = [available / n_cols] * n_cols

        # Cabecalho
        self.set_font('Helvetica', 'B', font_size)
        self.set_fill_color(21, 101, 192)
        self.set_text_color(255, 255, 255)

        for i, col in enumerate(df.columns):
            self.cell(col_widths[i], 6, sanitize_latin1(str(col)), border=1, fill=True, align='C')
        self.ln()

        # Dados
        self.set_font('Helvetica', '', font_size)
        self.set_text_color(40, 40, 40)
        alt = False
        for _, row in df.iterrows():
            if alt:
                self.set_fill_color(235, 240, 250)
            else:
                self.set_fill_color(255, 255, 255)
            alt = not alt

            if self.get_y() + 6 > self.h - 20:
                self.add_page()
                self.set_font('Helvetica', 'B', font_size)
                self.set_fill_color(21, 101, 192)
                self.set_text_color(255, 255, 255)
                for i, col in enumerate(df.columns):
                    self.cell(col_widths[i], 6, sanitize_latin1(str(col)), border=1, fill=True, align='C')
                self.ln()
                self.set_font('Helvetica', '', font_size)
                self.set_text_color(40, 40, 40)

            for i, val in enumerate(row):
                texto = str(val) if pd.notna(val) else ''
                max_chars = int(col_widths[i] / 1.7)
                if len(texto) > max_chars:
                    texto = texto[:max_chars-2] + '..'
                self.cell(col_widths[i], 6, sanitize_latin1(texto), border=1, fill=True, align='C')
            self.ln()

    def adicionar_imagem(self, path, w_mm=None):
        """Adiciona imagem centralizada na pagina."""
        if path is None or not os.path.exists(path):
            return
        if w_mm is None:
            w_mm = self.w - 30
        x = (self.w - w_mm) / 2
        if self.get_y() + 90 > self.h - 20:
            self.add_page()
        self.image(path, x=x, w=w_mm)
        self.ln(5)


# =============================================================================
# 5. GERAR O RELATORIO PDF
# =============================================================================
print("[*] Gerando graficos...")
path_barras_semanal = gerar_grafico_barras_semanal()
path_evolucao = gerar_grafico_evolucao_regional()
path_tipo_semana = gerar_grafico_tipo_por_semana()
path_auditorias = gerar_grafico_auditorias_semanal()

print("[*] Montando PDF...")
pdf = RelatorioPDF()
pdf.alias_nb_pages()

# ---------- CAPA ----------
pdf.add_page()
pdf.ln(25)
pdf.set_font('Helvetica', 'B', 26)
pdf.set_text_color(21, 101, 192)
pdf.cell(0, 15, sanitize_latin1('RELATORIO SEMANAL'), align='C', new_x='LMARGIN', new_y='NEXT')
pdf.set_font('Helvetica', '', 16)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 10, 'Atividades da Equipe de Qualidade', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(5)

pdf.set_draw_color(21, 101, 192)
pdf.set_line_width(1)
pdf.line(80, pdf.get_y(), pdf.w - 80, pdf.get_y())
pdf.ln(8)

pdf.set_font('Helvetica', '', 12)
pdf.set_text_color(100, 100, 100)

# Info da capa
all_dates = list(ativ_turbinas['data_inicio_exec']) + list(df_auditorias['data_inicio_exec'])
data_min = min(all_dates).strftime('%d/%m/%Y')
data_max = max(all_dates).strftime('%d/%m/%Y')
total_ativ_turbinas = len(ativ_turbinas)
total_ferramentas = ativ_auditorias['ferramentas_auditadas'].sum() if not ativ_auditorias.empty else 0

pdf.cell(0, 8, sanitize_latin1(f'Periodo: {data_min} a {data_max}'), align='C', new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 8, sanitize_latin1(f'Atividades em Turbinas: {total_ativ_turbinas}'), align='C', new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 8, sanitize_latin1(f'Ferramentas Auditadas (MPP6): {int(total_ferramentas)}'), align='C', new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 8, sanitize_latin1(f'Semanas: {len(semanas_ordenadas)}'), align='C', new_x='LMARGIN', new_y='NEXT')

all_regionais = sorted(set(
    list(ativ_turbinas['grupo_equipe'].unique()) +
    list(ativ_auditorias['grupo_equipe'].unique())
))
pdf.cell(0, 8, sanitize_latin1(f'Regionais: {", ".join(all_regionais)}'), align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(10)
pdf.set_font('Helvetica', 'I', 9)
pdf.cell(0, 6, sanitize_latin1(f'Gerado automaticamente em {datetime.now().strftime("%d/%m/%Y as %H:%M")}'), align='C', new_x='LMARGIN', new_y='NEXT')

# ---------- SECAO: VISAO GERAL (TURBINAS) ----------
pdf.add_page()
pdf.titulo_secao('1. VISAO GERAL - ATIVIDADES EM TURBINAS')

resumo_geral = ativ_turbinas.groupby(['ano_semana', 'periodo_semana']).agg(
    atividades=('aerogerador', 'count'),
    maquinas=('aerogerador', 'nunique'),
    parques=('parque', 'nunique'),
    os_total=('qtd_os', 'sum')
).reset_index()
resumo_geral.columns = ['Semana', 'Periodo', 'Atividades', 'Maquinas', 'Parques', 'Total OS']
resumo_geral = resumo_geral.sort_values('Semana')

pdf.adicionar_tabela(resumo_geral, col_widths=[25, 50, 30, 30, 25, 25])
pdf.ln(5)

pdf.adicionar_imagem(path_barras_semanal, w_mm=250)

# ---------- SECAO: EVOLUCAO POR REGIONAL (TURBINAS) ----------
pdf.add_page()
pdf.titulo_secao('2. EVOLUCAO SEMANAL POR REGIONAL (TURBINAS)')
pdf.adicionar_imagem(path_evolucao, w_mm=250)

pivot_sr = ativ_turbinas.pivot_table(
    index='ano_semana', columns='grupo_equipe',
    values='aerogerador', aggfunc='count', fill_value=0
)
pivot_sr = pivot_sr.reindex(semanas_ordenadas, fill_value=0)
pivot_sr['TOTAL'] = pivot_sr.sum(axis=1)
pivot_sr = pivot_sr.reset_index()
pivot_sr.columns.name = None
pivot_sr.rename(columns={'ano_semana': 'Semana'}, inplace=True)

n_cols_sr = len(pivot_sr.columns)
cw_sr = [28] + [int((277-28) / (n_cols_sr-1))] * (n_cols_sr-1)
pdf.adicionar_tabela(pivot_sr, col_widths=cw_sr)

# ---------- SECAO: TIPO POR SEMANA (TURBINAS) ----------
pdf.add_page()
pdf.titulo_secao('3. ATIVIDADES EM TURBINAS POR TIPO')
pdf.adicionar_imagem(path_tipo_semana, w_mm=250)

# ---------- SECAO: AUDITORIAS DE FERRAMENTAS (POR REGIONAL) ----------
pdf.add_page()
pdf.titulo_secao('4. AUDITORIAS DE FERRAMENTAS (MPP6) - POR REGIONAL')

pdf.set_font('Helvetica', '', 9)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 6, sanitize_latin1(
    'As auditorias de ferramentas sao contabilizadas por REGIONAL (quantidade de ferramentas auditadas),'
), new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 6, sanitize_latin1(
    'e nao por turbina ou parque, pois os codigos referem-se a patrimonios de ferramentas.'
), new_x='LMARGIN', new_y='NEXT')
pdf.ln(3)

# Tabela resumo geral auditorias por regional
if not ativ_auditorias.empty:
    resumo_aud_regional = ativ_auditorias.groupby('grupo_equipe').agg(
        semanas=('ano_semana', 'nunique'),
        ferramentas=('ferramentas_auditadas', 'sum'),
        os_total=('qtd_os', 'sum')
    ).reset_index()
    resumo_aud_regional.columns = ['Regional', 'Semanas Ativas', 'Ferramentas Auditadas', 'Total OS']
    resumo_aud_regional = resumo_aud_regional.sort_values('Ferramentas Auditadas', ascending=False)

    pdf.titulo_secao('Resumo Acumulado por Regional', nivel=3)
    pdf.adicionar_tabela(resumo_aud_regional, col_widths=[40, 40, 50, 40])
    pdf.ln(5)

    # Tabela semanal auditorias
    resumo_aud_semanal = ativ_auditorias.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='ferramentas_auditadas', aggfunc='sum', fill_value=0
    )
    resumo_aud_semanal = resumo_aud_semanal.reindex(semanas_ordenadas, fill_value=0)
    resumo_aud_semanal['TOTAL'] = resumo_aud_semanal.sum(axis=1)
    resumo_aud_semanal = resumo_aud_semanal.reset_index()
    resumo_aud_semanal.columns.name = None
    resumo_aud_semanal.rename(columns={'ano_semana': 'Semana'}, inplace=True)

    pdf.titulo_secao('Ferramentas Auditadas por Semana x Regional', nivel=3)
    n_cols_aud = len(resumo_aud_semanal.columns)
    cw_aud = [28] + [int((277-28) / (n_cols_aud-1))] * (n_cols_aud-1)
    pdf.adicionar_tabela(resumo_aud_semanal, col_widths=cw_aud)
    pdf.ln(5)

    # Grafico auditorias
    if path_auditorias:
        pdf.adicionar_imagem(path_auditorias, w_mm=250)

# ---------- SECAO: DETALHE SEMANA A SEMANA ----------
pdf.add_page()
pdf.titulo_secao('5. DETALHAMENTO SEMANAL - TURBINAS E AUDITORIAS')

for semana in semanas_ordenadas:
    df_sem_turb = ativ_turbinas[ativ_turbinas['ano_semana'] == semana]
    df_sem_aud = ativ_auditorias[ativ_auditorias['ano_semana'] == semana]

    if df_sem_turb.empty and df_sem_aud.empty:
        continue

    periodo = ''
    if not df_sem_turb.empty:
        periodo = df_sem_turb['periodo_semana'].iloc[0]
    elif not df_sem_aud.empty:
        periodo = df_sem_aud['periodo_semana'].iloc[0]

    total_turb = len(df_sem_turb)
    total_ferr = df_sem_aud['ferramentas_auditadas'].sum() if not df_sem_aud.empty else 0

    # Titulo da semana
    titulo = f'{semana} ({periodo})'
    if total_turb > 0 and total_ferr > 0:
        titulo += f' - {total_turb} ativ. turbinas + {int(total_ferr)} ferram. auditadas'
    elif total_turb > 0:
        titulo += f' - {total_turb} atividades em turbinas'
    else:
        titulo += f' - {int(total_ferr)} ferramentas auditadas'

    pdf.titulo_secao(titulo, nivel=2)

    # --- PARTE 1: TURBINAS ---
    if total_turb > 0:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(21, 101, 192)
        pdf.cell(0, 5, 'ATIVIDADES EM TURBINAS:', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

        # Tabela resumo por regional
        tab_regional = tabela_semanal_regional_turbinas(semana)
        if not tab_regional.empty:
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, 'Resumo por Regional:', new_x='LMARGIN', new_y='NEXT')
            pdf.adicionar_tabela(tab_regional, col_widths=[30, 30, 35, 25, 22, 25])
            pdf.ln(3)

        # Tabela detalhe por maquinas
        tab_maquinas = tabela_semanal_maquinas(semana)
        if not tab_maquinas.empty:
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, 'Turbinas atendidas:', new_x='LMARGIN', new_y='NEXT')
            pdf.adicionar_tabela(tab_maquinas,
                                 col_widths=[22, 26, 20, 80, 22, 107],
                                 font_size=6)
            pdf.ln(3)

        # Grafico de maquinas da semana
        path_maq = gerar_grafico_maquinas_por_semana(semana)
        if path_maq:
            pdf.adicionar_imagem(path_maq, w_mm=200)

    # --- PARTE 2: AUDITORIAS (por regional) ---
    if not df_sem_aud.empty and total_ferr > 0:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(230, 81, 0)  # Cor laranja para diferenciar
        pdf.cell(0, 5, 'AUDITORIAS DE FERRAMENTAS (MPP6) - por Regional:', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

        tab_aud = tabela_semanal_auditorias(semana)
        if not tab_aud.empty:
            pdf.adicionar_tabela(tab_aud, col_widths=[40, 50, 30])
            pdf.ln(3)

    pdf.ln(3)
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()

# ---------- SECAO FINAL: RESUMO ACUMULADO ----------
pdf.add_page()
pdf.titulo_secao('6. RESUMO ACUMULADO')

# Total turbinas por regional
total_regional = ativ_turbinas.groupby('grupo_equipe').agg(
    atividades=('aerogerador', 'count'),
    maquinas=('aerogerador', 'nunique'),
    parques=('parque', 'nunique'),
    os_total=('qtd_os', 'sum')
).reset_index()
total_regional.columns = ['Regional', 'Total Atividades', 'Maquinas Distintas', 'Parques', 'Total OS']
pdf.titulo_secao('Atividades em Turbinas - Total por Regional', nivel=3)
pdf.adicionar_tabela(total_regional, col_widths=[35, 40, 45, 30, 30])
pdf.ln(5)

# Total turbinas por tipo
total_tipo = ativ_turbinas.groupby('desc_esquema').agg(
    atividades=('aerogerador', 'count'),
    maquinas=('aerogerador', 'nunique'),
).reset_index()
total_tipo.columns = ['Tipo de Atividade', 'Total Atividades', 'Maquinas Distintas']
total_tipo = total_tipo.sort_values('Total Atividades', ascending=False)
pdf.titulo_secao('Atividades em Turbinas - Total por Tipo', nivel=3)
pdf.adicionar_tabela(total_tipo, col_widths=[130, 40, 45])
pdf.ln(5)

# Top maquinas mais atendidas (somente turbinas)
top_maq = ativ_turbinas.groupby(['aerogerador', 'parque', 'grupo_equipe']).agg(
    atividades=('desc_esquema', 'count'),
    tipos=('desc_esquema', lambda x: ', '.join(sorted(x.unique())))
).reset_index().sort_values('atividades', ascending=False).head(20)
top_maq.columns = ['Aerogerador', 'Parque', 'Regional', 'Atividades', 'Tipos']
pdf.titulo_secao('Top 20 Turbinas Mais Atendidas', nivel=3)
pdf.adicionar_tabela(top_maq, col_widths=[28, 20, 25, 25, 180])
pdf.ln(5)

# Total auditorias por regional
if not ativ_auditorias.empty:
    pdf.titulo_secao('Auditorias de Ferramentas - Total por Regional', nivel=3)
    resumo_aud_final = ativ_auditorias.groupby('grupo_equipe').agg(
        ferramentas=('ferramentas_auditadas', 'sum'),
        os_total=('qtd_os', 'sum')
    ).reset_index()
    resumo_aud_final.columns = ['Regional', 'Total Ferramentas Auditadas', 'Total OS']
    pdf.adicionar_tabela(resumo_aud_final, col_widths=[40, 60, 40])

# =============================================================================
# 6. SALVAR PDF
# =============================================================================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARQUIVO_PDF_SAIDA)
pdf.output(output_path)

print(f"\n{'='*60}")
print(f"[OK] PDF GERADO COM SUCESSO!")
print(f"{'='*60}")
print(f"Arquivo: {output_path}")
print(f"Atividades em turbinas: {len(ativ_turbinas)}")
print(f"Ferramentas auditadas (MPP6): {int(total_ferramentas)}")
print(f"Semanas: {len(semanas_ordenadas)}")
print(f"Regionais: {', '.join(all_regionais)}")
print(f"Maquinas (turbinas) distintas: {ativ_turbinas['aerogerador'].nunique()}")
print(f"{'='*60}")

# Limpar arquivos temporarios
import shutil
try:
    shutil.rmtree(TEMP_DIR)
except:
    pass
