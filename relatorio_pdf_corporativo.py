# =============================================================================
# RELATORIO PDF CORPORATIVO - Design Premium Energimp
# =============================================================================
# Paleta: Azul Marinho (#0D1B3E), Ciano (#00ACC1), Coral (#FF6B6B)
# Fonte: Helvetica (sans-serif, built-in FPDF)
# Layout: A4 Landscape, limpo e técnico
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from fpdf import FPDF
import os
import tempfile
from datetime import datetime
import unicodedata

# =============================================================================
# PALETA DE CORES
# =============================================================================
NAVY    = (13, 27, 62)       # #0D1B3E - títulos, cabeçalhos
CYAN    = (0, 172, 193)      # #00ACC1 - métricas, destaques
CORAL   = (255, 107, 107)    # #FF6B6B - alertas, diferenças
WHITE   = (255, 255, 255)
LGRAY   = (245, 247, 250)    # #F5F7FA - linhas alternadas
DGRAY   = (55, 71, 79)       # #37474F - texto corpo
MGRAY   = (120, 130, 140)    # texto secundário

NAVY_HEX  = '#0D1B3E'
CYAN_HEX  = '#00ACC1'
CORAL_HEX = '#FF6B6B'

CORES_REGIONAL = {
    'AGD': '#1565C0', 'CE': '#E65100',
    'BJS': '#2E7D32', 'OUTROS': '#757575'
}

# Configuração matplotlib
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 9,
    'axes.titlesize': 12, 'axes.titleweight': 'bold',
    'axes.labelsize': 10, 'figure.facecolor': '#FFFFFF',
    'axes.facecolor': '#FFFFFF', 'axes.grid': True,
    'grid.alpha': 0.2, 'grid.linestyle': '--',
    'axes.spines.top': False, 'axes.spines.right': False,
})


def sanitize_latin1(text):
    """Converte texto para latin-1 compatível."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2022': '*',
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
# GERAÇÃO DE GRÁFICOS
# =============================================================================

def gerar_grafico_waterfall(categorias, valores, titulo, temp_dir):
    """Gráfico waterfall/cascata para decomposição de atividades."""
    fig, ax = plt.subplots(figsize=(14, 5.5))
    n = len(categorias)
    running = 0

    for i, (cat, val) in enumerate(zip(categorias, valores)):
        color = CYAN_HEX if val >= 0 else CORAL_HEX
        ax.bar(i, val, bottom=running, color=color, edgecolor='white', width=0.55)
        label_y = running + val / 2
        ax.text(i, label_y, f'{int(val)}', ha='center', va='center',
                fontweight='bold', fontsize=9, color='white' if abs(val) > 2 else NAVY_HEX)
        if i < n - 1:
            ax.plot([i + 0.28, i + 0.72], [running + val] * 2,
                    color='#bbb', linewidth=0.7, linestyle='--')
        running += val

    # Barra total
    ax.bar(n, running, color=NAVY_HEX, edgecolor='white', width=0.55)
    ax.text(n, running / 2, f'{int(running)}', ha='center', va='center',
            fontweight='bold', fontsize=11, color='white')

    ax.set_xticks(range(n + 1))
    labels = list(categorias) + ['TOTAL']
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ax.set_title(titulo, fontweight='bold', fontsize=13, color=NAVY_HEX, pad=12)
    ax.set_ylabel('Atividades', fontweight='bold')
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(temp_dir, 'waterfall.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def gerar_grafico_barras_semanal(ativ_turbinas, semanas, temp_dir):
    """Barras empilhadas: atividades por semana × regional."""
    pivot = ativ_turbinas.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='aerogerador', aggfunc='count', fill_value=0
    ).reindex(semanas, fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5.5))
    cores = [CORES_REGIONAL.get(c, '#9E9E9E') for c in pivot.columns]
    pivot.plot(kind='bar', stacked=True, ax=ax, color=cores,
              edgecolor='white', linewidth=0.6, width=0.7)

    for i, sem in enumerate(pivot.index):
        total = pivot.loc[sem].sum()
        ax.annotate(f'{int(total)}', xy=(i, total), xytext=(0, 4),
                    textcoords="offset points", ha='center', fontsize=9,
                    fontweight='bold', color=NAVY_HEX)

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Atividades', fontweight='bold')
    ax.set_title('Atividades em Turbinas por Semana', fontsize=13,
                 fontweight='bold', color=NAVY_HEX, pad=10)
    ax.legend(title='Regional', bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)
    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(temp_dir, 'barras_semanal.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


def gerar_grafico_evolucao(ativ_turbinas, semanas, temp_dir):
    """Gráfico de linhas: evolução semanal por regional."""
    pivot = ativ_turbinas.pivot_table(
        index='ano_semana', columns='grupo_equipe',
        values='aerogerador', aggfunc='count', fill_value=0
    ).reindex(semanas, fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 5))
    for regional in pivot.columns:
        cor = CORES_REGIONAL.get(regional, '#9E9E9E')
        ax.plot(pivot.index, pivot[regional], marker='o', linewidth=2.5,
                markersize=6, label=regional, color=cor, zorder=3)
        for x, y in zip(pivot.index, pivot[regional]):
            if y > 0:
                ax.annotate(str(int(y)), (x, y), textcoords="offset points",
                            xytext=(0, 8), ha='center', fontsize=7.5,
                            fontweight='bold', color=cor)

    ax.set_xlabel('Semana', fontweight='bold')
    ax.set_ylabel('Atividades', fontweight='bold')
    ax.set_title('Evolucao Semanal por Regional', fontsize=13,
                 fontweight='bold', color=NAVY_HEX, pad=10)
    ax.legend(fontsize=9, loc='upper left')
    labels = [s.replace('-S', '\nS') for s in pivot.index]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    path = os.path.join(temp_dir, 'evolucao.png')
    plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close()
    return path


# =============================================================================
# CLASSE PDF CORPORATIVA
# =============================================================================

class RelatorioCorporativo(FPDF):
    def __init__(self, logo_path=None):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Linha superior azul marinho
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 3, 'F')

        # Logo ou nome da empresa
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 5, 35)
        else:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(*NAVY)
            self.set_xy(10, 6)
            self.cell(40, 8, 'energimp', align='L')

        # Título do relatório
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*NAVY)
        self.set_xy(50, 6)
        self.cell(0, 4, sanitize_latin1('Relatorio Semanal de Atividades'), align='L')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*MGRAY)
        self.set_xy(50, 10)
        self.cell(0, 4, 'Equipe de Qualidade - Energimp', align='L')

        # Data de geração
        self.set_font('Helvetica', '', 7)
        self.set_xy(-60, 7)
        self.cell(50, 4, f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='R')

        # Linha separadora
        self.set_draw_color(*NAVY)
        self.set_line_width(0.4)
        self.line(10, 17, self.w - 10, 17)
        self.set_y(20)

    def footer(self):
        self.set_y(-16)
        # Linha
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(2)
        # Confidencialidade
        self.set_font('Helvetica', 'I', 6)
        self.set_text_color(*MGRAY)
        self.cell(0, 4, sanitize_latin1(
            'CONFIDENCIAL - Documento de uso interno Energimp. '
            'Distribuicao nao autorizada e proibida.'
        ), align='L')
        # Numeração
        self.set_font('Helvetica', '', 7)
        self.cell(0, 4, sanitize_latin1(f'Pagina {self.page_no()}/{{nb}}'), align='R')

    def titulo_secao(self, texto, nivel=1):
        if nivel == 1:
            self.set_font('Helvetica', 'B', 15)
            self.set_text_color(*NAVY)
        elif nivel == 2:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*DGRAY)
        else:
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*MGRAY)
        self.cell(0, 8, sanitize_latin1(texto), new_x='LMARGIN', new_y='NEXT')
        if nivel == 1:
            self.set_draw_color(*CYAN)
            self.set_line_width(0.8)
            self.line(self.l_margin, self.get_y(), self.l_margin + 60, self.get_y())
        self.ln(3)

    def draw_kpi_card(self, x, y, w, h, label, value, accent_color=NAVY):
        """Desenha card de KPI com acento colorido no topo."""
        # Sombra sutil
        self.set_fill_color(230, 230, 230)
        self.rect(x + 1, y + 1, w, h, 'F')
        # Fundo branco
        self.set_fill_color(*WHITE)
        self.rect(x, y, w, h, 'F')
        # Borda
        self.set_draw_color(220, 225, 230)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, 'D')
        # Acento no topo
        self.set_fill_color(*accent_color)
        self.rect(x, y, w, 2.5, 'F')
        # Valor
        self.set_xy(x, y + 8)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(*NAVY)
        self.cell(w, 12, str(value), align='C')
        # Label
        self.set_xy(x, y + 22)
        self.set_font('Helvetica', '', 7.5)
        self.set_text_color(*MGRAY)
        self.cell(w, 5, sanitize_latin1(label), align='C')

    def kpi_row(self, kpis, y=None):
        """Desenha uma linha de KPIs. kpis = [(label, value, color), ...]"""
        if y is None:
            y = self.get_y()
        n = len(kpis)
        total_w = self.w - 20
        gap = 6
        card_w = (total_w - (n - 1) * gap) / n
        card_h = 35

        for i, (label, value, color) in enumerate(kpis):
            x = 10 + i * (card_w + gap)
            self.draw_kpi_card(x, y, card_w, card_h, label, value, color)

        self.set_y(y + card_h + 8)

    def tabela_corporativa(self, df, col_widths=None, font_size=7):
        """Tabela minimalista com estilo corporativo."""
        if df.empty:
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 6, 'Sem dados disponiveis.', new_x='LMARGIN', new_y='NEXT')
            return

        n_cols = len(df.columns)
        if col_widths is None:
            available = self.w - 20
            col_widths = [available / n_cols] * n_cols

        row_h = 6

        def draw_header():
            self.set_font('Helvetica', 'B', font_size)
            self.set_fill_color(*NAVY)
            self.set_text_color(*WHITE)
            for i, col in enumerate(df.columns):
                self.cell(col_widths[i], row_h, sanitize_latin1(str(col)),
                          border=0, fill=True, align='C')
            self.ln()

        draw_header()
        self.set_font('Helvetica', '', font_size)
        alt = False

        for _, row in df.iterrows():
            if self.get_y() + row_h > self.h - 22:
                self.add_page()
                draw_header()
                self.set_font('Helvetica', '', font_size)

            if alt:
                self.set_fill_color(*LGRAY)
            else:
                self.set_fill_color(*WHITE)
            alt = not alt
            self.set_text_color(*DGRAY)

            for i, val in enumerate(row):
                texto = str(val) if pd.notna(val) else ''
                max_chars = int(col_widths[i] / 1.7)
                if len(texto) > max_chars:
                    texto = texto[:max_chars - 2] + '..'
                self.cell(col_widths[i], row_h, sanitize_latin1(texto),
                          border=0, fill=True, align='C')
            self.ln()

        # Linha final
        self.set_draw_color(200, 205, 210)
        self.set_line_width(0.3)
        total_w = sum(col_widths)
        self.line(self.l_margin, self.get_y(), self.l_margin + total_w, self.get_y())

    def adicionar_imagem(self, path, w_mm=None):
        """Adiciona imagem centralizada."""
        if not path or not os.path.exists(path):
            return
        if w_mm is None:
            w_mm = self.w - 30
        x = (self.w - w_mm) / 2
        if self.get_y() + 80 > self.h - 22:
            self.add_page()
        self.image(path, x=x, w=w_mm)
        self.ln(5)


# =============================================================================
# FUNÇÃO PRINCIPAL: GERAR RELATÓRIO
# =============================================================================

def gerar_relatorio_pdf(ativ_turbinas, ativ_auditorias, pcm_atividades,
                         output_path=None, logo_path=None):
    """
    Gera o relatório PDF corporativo completo.

    Args:
        ativ_turbinas: DataFrame de atividades em turbinas
        ativ_auditorias: DataFrame de auditorias
        pcm_atividades: lista de dicts com atividades planejadas (PCM)
        output_path: caminho do PDF de saída
        logo_path: caminho do logotipo
    """
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'Relatorio_Semanal_Atividades_Qualidade.pdf'
        )

    temp_dir = tempfile.mkdtemp()

    # Calcular semanas
    semanas = sorted(set(
        list(ativ_turbinas['ano_semana'].unique()) if not ativ_turbinas.empty else []
    ) | set(
        list(ativ_auditorias['ano_semana'].unique()) if not ativ_auditorias.empty else []
    ))

    # Gerar gráficos
    path_barras = None
    path_evolucao = None
    path_waterfall = None

    if not ativ_turbinas.empty:
        path_barras = gerar_grafico_barras_semanal(ativ_turbinas, semanas, temp_dir)
        path_evolucao = gerar_grafico_evolucao(ativ_turbinas, semanas, temp_dir)

        # Waterfall por tipo de atividade
        tipos = ativ_turbinas['desc_esquema'].value_counts()
        path_waterfall = gerar_grafico_waterfall(
            tipos.index.tolist(), tipos.values.tolist(),
            'Decomposicao de Atividades por Tipo', temp_dir
        )

    # --- MONTAR PDF ---
    pdf = RelatorioCorporativo(logo_path=logo_path)
    pdf.alias_nb_pages()

    # ===== CAPA =====
    pdf.add_page()
    pdf.ln(20)
    # Linha decorativa
    pdf.set_fill_color(*NAVY)
    pdf.rect(10, 40, 5, 60, 'F')
    pdf.set_fill_color(*CYAN)
    pdf.rect(10, 100, 5, 3, 'F')

    pdf.set_xy(25, 42)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 14, sanitize_latin1('RELATORIO SEMANAL'), new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(25)
    pdf.set_font('Helvetica', '', 16)
    pdf.set_text_color(*DGRAY)
    pdf.cell(0, 10, 'Atividades da Equipe de Qualidade', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(10)

    # Info da capa
    pdf.set_x(25)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*MGRAY)

    total_turb = len(ativ_turbinas) if not ativ_turbinas.empty else 0
    total_ferr = int(ativ_auditorias['ferramentas_auditadas'].sum()) if not ativ_auditorias.empty else 0
    total_pcm = len(pcm_atividades) if pcm_atividades else 0

    if not ativ_turbinas.empty:
        all_dates = list(ativ_turbinas['data_inicio_exec'])
        data_min = min(all_dates).strftime('%d/%m/%Y')
        data_max = max(all_dates).strftime('%d/%m/%Y')
    else:
        data_min = data_max = '-'

    infos = [
        f'Periodo: {data_min} a {data_max}',
        f'Atividades em Turbinas: {total_turb}',
        f'Ferramentas Auditadas: {total_ferr}',
        f'Semanas: {len(semanas)}',
        f'Atividades Planejadas (PCM): {total_pcm}',
    ]
    for info in infos:
        pdf.set_x(25)
        pdf.cell(0, 7, sanitize_latin1(info), new_x='LMARGIN', new_y='NEXT')

    pdf.ln(8)
    pdf.set_x(25)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.cell(0, 5, sanitize_latin1(
        f'Gerado automaticamente em {datetime.now().strftime("%d/%m/%Y as %H:%M")}'
    ), new_x='LMARGIN', new_y='NEXT')

    # ===== VISÃO GERAL COM KPIs =====
    pdf.add_page()
    pdf.titulo_secao('1. VISAO GERAL')

    maq_distintas = ativ_turbinas['aerogerador'].nunique() if not ativ_turbinas.empty else 0
    parques = ativ_turbinas['parque'].nunique() if not ativ_turbinas.empty else 0

    pdf.kpi_row([
        ('ATIVIDADES EM TURBINAS', total_turb, NAVY),
        ('MAQUINAS DISTINTAS', maq_distintas, CYAN),
        ('PARQUES ATENDIDOS', parques, (76, 175, 80)),
        ('SEMANAS', len(semanas), CORAL),
    ])

    # Gráfico waterfall
    if path_waterfall:
        pdf.adicionar_imagem(path_waterfall, w_mm=240)

    # ===== EVOLUÇÃO SEMANAL =====
    if not ativ_turbinas.empty:
        pdf.add_page()
        pdf.titulo_secao('2. EVOLUCAO SEMANAL')

        resumo = ativ_turbinas.groupby(['ano_semana', 'periodo_semana']).agg(
            atividades=('aerogerador', 'count'),
            maquinas=('aerogerador', 'nunique'),
            parques=('parque', 'nunique'),
            os_total=('qtd_os', 'sum')
        ).reset_index().sort_values('ano_semana')
        resumo.columns = ['Semana', 'Periodo', 'Atividades', 'Maquinas', 'Parques', 'OS']

        pdf.tabela_corporativa(resumo, col_widths=[25, 48, 28, 28, 25, 25])
        pdf.ln(5)
        pdf.adicionar_imagem(path_barras, w_mm=240)

        # Evolução por regional
        pdf.add_page()
        pdf.titulo_secao('3. EVOLUCAO POR REGIONAL', nivel=1)
        pdf.adicionar_imagem(path_evolucao, w_mm=240)

    # ===== HELPER: Renderizar detalhe de uma semana =====
    def render_semana_pdf(df_semana, titulo, subtitulo=''):
        """Renderiza tabelas de detalhe de uma semana no PDF."""
        if df_semana.empty:
            pdf.set_font('Helvetica', 'I', 8)
            pdf.set_text_color(*MGRAY)
            pdf.cell(0, 6, sanitize_latin1('Sem atividades registradas nesta semana.'),
                     new_x='LMARGIN', new_y='NEXT')
            pdf.ln(3)
            return

        if subtitulo:
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(*MGRAY)
            pdf.cell(0, 5, sanitize_latin1(subtitulo), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)

        # Resumo por regional
        resumo_reg = df_semana.groupby('grupo_equipe').agg(
            atividades=('aerogerador', 'count'),
            maquinas=('aerogerador', 'nunique'),
            parques=('parque', 'nunique'),
        ).reset_index()
        resumo_reg.columns = ['Regional', 'Atividades', 'Maquinas', 'Parques']
        pdf.titulo_secao('Resumo por Regional', nivel=3)
        pdf.tabela_corporativa(resumo_reg, col_widths=[35, 35, 40, 35])
        pdf.ln(4)

        # Detalhe por turbina
        detalhe = df_semana.groupby(['grupo_equipe', 'aerogerador', 'parque']).agg(
            tipo=('desc_esquema', lambda x: ' | '.join(sorted(x.unique()))),
            qtd=('desc_esquema', 'count'),
        ).reset_index()
        detalhe.columns = ['Regional', 'Aerogerador', 'Parque', 'Tipo', 'Qtd']
        pdf.titulo_secao('Turbinas Atendidas', nivel=3)
        pdf.tabela_corporativa(detalhe, col_widths=[25, 28, 22, 130, 20])
        pdf.ln(3)

    # ===== Calcular semanas: anterior, atual, próxima =====
    if not ativ_turbinas.empty:
        import datetime as dt_module
        hoje = dt_module.date.today()

        def info_semana(ref, offset=0):
            target = ref + dt_module.timedelta(weeks=offset)
            inicio = target - dt_module.timedelta(days=target.weekday())
            fim = inicio + dt_module.timedelta(days=6)
            sn = target.isocalendar()[1]
            ano = target.isocalendar()[0]
            return {
                'num': sn, 'ano': ano,
                'periodo': f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}",
                'label': f"{ano}-S{str(sn).zfill(2)}"
            }

        sem_ant = info_semana(hoje, -1)
        sem_cur = info_semana(hoje, 0)
        sem_prx = info_semana(hoje, 1)

        # ===== SEMANA ANTERIOR =====
        df_sem_ant = ativ_turbinas[ativ_turbinas['ano_semana'] == sem_ant['label']]
        if not df_sem_ant.empty:
            pdf.add_page()
            pdf.titulo_secao(
                f'4. SEMANA ANTERIOR - S{sem_ant["num"]} ({sem_ant["periodo"]})'
            )
            render_semana_pdf(
                df_sem_ant,
                f'Semana {sem_ant["num"]}',
                f'Atividades realizadas na semana anterior ({sem_ant["periodo"]})'
            )

        # ===== SEMANA ATUAL =====
        df_sem_cur = ativ_turbinas[ativ_turbinas['ano_semana'] == sem_cur['label']]
        secao_num_atual = 5 if not df_sem_ant.empty else 4
        pdf.add_page()
        pdf.titulo_secao(
            f'{secao_num_atual}. SEMANA ATUAL - S{sem_cur["num"]} ({sem_cur["periodo"]})'
        )
        if not df_sem_cur.empty:
            render_semana_pdf(
                df_sem_cur,
                f'Semana {sem_cur["num"]}',
                f'Atividades realizadas na semana atual ({sem_cur["periodo"]})'
            )
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(*MGRAY)
            pdf.cell(0, 6, sanitize_latin1(
                'Sem atividades registradas para a semana atual ate o momento.'
            ), new_x='LMARGIN', new_y='NEXT')

    # ===== PLANEJAMENTO PCM - PRÓXIMA SEMANA =====
    secao_pcm = (secao_num_atual + 1) if (not ativ_turbinas.empty and 'secao_num_atual' in dir()) else 4
    if pcm_atividades:
        pdf.add_page()
        pdf.titulo_secao(
            f'{secao_pcm}. PLANEJAMENTO PCM - PROXIMA SEMANA S{sem_prx["num"] if not ativ_turbinas.empty else ""}'
        )

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*DGRAY)
        pdf.cell(0, 6, sanitize_latin1(
            'Atividades planejadas informadas pela equipe de PCM para a proxima semana.'
        ), new_x='LMARGIN', new_y='NEXT')
        if not ativ_turbinas.empty:
            pdf.cell(0, 6, sanitize_latin1(
                f'Periodo: {sem_prx["periodo"]}'
            ), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(3)

        # KPI do planejamento
        regs_planejadas = set(a.get('regional', '') for a in pcm_atividades)
        pdf.kpi_row([
            ('ATIVIDADES PLANEJADAS', len(pcm_atividades), CYAN),
            ('REGIONAIS', len(regs_planejadas), NAVY),
        ])

        df_pcm = pd.DataFrame(pcm_atividades)
        cols_exibir = ['regional', 'parque', 'aerogerador', 'tipo_atividade',
                       'data_prevista', 'responsavel', 'observacoes']
        cols_presentes = [c for c in cols_exibir if c in df_pcm.columns]
        df_show = df_pcm[cols_presentes].copy()
        df_show.columns = [c.replace('_', ' ').title() for c in cols_presentes]

        widths = {
            'Regional': 22, 'Parque': 20, 'Aerogerador': 25,
            'Tipo Atividade': 75, 'Data Prevista': 25,
            'Responsavel': 30, 'Observacoes': 80
        }
        cw = [widths.get(c, 30) for c in df_show.columns]
        pdf.tabela_corporativa(df_show, col_widths=cw)

    # ===== RESUMO ACUMULADO =====
    if not ativ_turbinas.empty:
        pdf.add_page()
        num_secao = secao_pcm + 1 if pcm_atividades else secao_pcm
        pdf.titulo_secao(f'{num_secao}. RESUMO ACUMULADO')

        # Por regional
        total_reg = ativ_turbinas.groupby('grupo_equipe').agg(
            atividades=('aerogerador', 'count'),
            maquinas=('aerogerador', 'nunique'),
            parques=('parque', 'nunique'),
            os_total=('qtd_os', 'sum')
        ).reset_index()
        total_reg.columns = ['Regional', 'Atividades', 'Maquinas', 'Parques', 'OS Total']
        pdf.titulo_secao('por Regional', nivel=3)
        pdf.tabela_corporativa(total_reg, col_widths=[35, 35, 40, 30, 30])
        pdf.ln(5)

        # Por tipo
        total_tipo = ativ_turbinas.groupby('desc_esquema').agg(
            atividades=('aerogerador', 'count'),
            maquinas=('aerogerador', 'nunique'),
        ).reset_index().sort_values('atividades', ascending=False)
        total_tipo.columns = ['Tipo de Atividade', 'Atividades', 'Maquinas']
        pdf.titulo_secao('por Tipo de Atividade', nivel=3)
        pdf.tabela_corporativa(total_tipo, col_widths=[140, 40, 40])

    # ===== SALVAR =====
    pdf.output(output_path)

    # Limpar temporários
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    return output_path
