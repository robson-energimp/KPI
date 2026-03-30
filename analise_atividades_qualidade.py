# =============================================================================
# ANÁLISE DE ATIVIDADES DA EQUIPE DE QUALIDADE - AEROGERADORES
# =============================================================================
# Uma ATIVIDADE = 1 inspeção completa em um aerogerador (contém ~6 OS).
# As atividades são separadas por tipo usando desc_esquema diretamente.
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.cm as cm
import re

# =============================================================================
# CÉLULA 1 - Preparação dos dados da equipe QLW
# (Rodar após as consultas originais que criam o CondOS_WTG)
# =============================================================================

def equipe_grupo(cod_equipe):
    cod = str(cod_equipe).upper()
    if 'CE' in cod:
        return 'CE'
    elif 'BJS' in cod:
        return 'BJS'
    elif 'AGD' in cod:
        return 'AGD'
    else:
        return 'OUTROS'

# Filtrar OS da equipe de Qualidade e aplicar grupo
OS_QLW = CondOS_WTG[CondOS_WTG['desc_numero_os'].str.contains('QLW', na=False)].copy()
OS_QLW['grupo_equipe'] = OS_QLW['cod_equipe'].apply(equipe_grupo)

# Remover duplicatas causadas pelo JOIN com desc_carac/resposta
OS_QLW_unico = OS_QLW.drop_duplicates(subset=['cod_os']).copy()

# =============================================================================
# CÉLULA 2 - Verificar todos os cod_esquema e desc_esquema existentes
# =============================================================================

print("="*80)
print("VALORES ÚNICOS DE cod_esquema / desc_esquema na equipe QLW:")
print("="*80)
esquemas = OS_QLW_unico.groupby(['cod_esquema', 'desc_esquema']).agg(
    qtd_os=('cod_os', 'nunique')
).reset_index().sort_values('qtd_os', ascending=False)
print(esquemas.to_string(index=False))

print("\n" + "="*80)
print("VALORES ÚNICOS DE cod_especie / desc_especie:")
print("="*80)
especies = OS_QLW_unico.groupby(['cod_especie', 'desc_especie']).agg(
    qtd_os=('cod_os', 'nunique')
).reset_index().sort_values('qtd_os', ascending=False)
print(especies.to_string(index=False))

# =============================================================================
# CÉLULA 3 - CLASSIFICAÇÃO E AGRUPAMENTO EM ATIVIDADES
# =============================================================================
# Usa desc_esquema diretamente como tipo de atividade.
# Apenas "AVALIAÇÃO DE EQUIPE" é tratada como OS complementar.
# =============================================================================

# Extrair data e parque
OS_QLW_unico['data_atividade'] = pd.to_datetime(OS_QLW_unico['data_inicio_exec']).dt.date
OS_QLW_unico['parque'] = OS_QLW_unico['aerogerador'].str[:3]

# Separar OS complementares (Avaliação de Equipe acompanha outra inspeção)
OS_QLW_unico['eh_avaliacao'] = OS_QLW_unico['desc_esquema'].str.upper().str.contains('AVALIAÇÃO DE EQUIPE', na=False)

OS_principais = OS_QLW_unico[~OS_QLW_unico['eh_avaliacao']].copy()
OS_avaliacoes = OS_QLW_unico[OS_QLW_unico['eh_avaliacao']].copy()

# Tipo da atividade = desc_esquema diretamente (sem mapeamento manual)
OS_principais['tipo_atividade'] = OS_principais['desc_esquema']

# Agrupar OS em ATIVIDADES:
# Chave: grupo_equipe + data + aerogerador + tipo_atividade
atividades = OS_principais.groupby(
    ['grupo_equipe', 'data_atividade', 'aerogerador', 'parque', 'tipo_atividade']
).agg(
    qtd_os=('cod_os', 'nunique'),
    componentes=('desc_especie', lambda x: ', '.join(sorted(x.unique()))),
    cod_esquema=('cod_esquema', 'first'),
    inicio=('data_inicio_exec', 'min'),
    fim=('data_fim_exec', 'max')
).reset_index()

# Verificar se teve Avaliação de Equipe associada
avaliacoes_resumo = OS_avaliacoes.groupby(
    ['data_atividade', 'aerogerador']
).agg(teve_avaliacao=('cod_os', 'nunique')).reset_index()

atividades = atividades.merge(
    avaliacoes_resumo, on=['data_atividade', 'aerogerador'], how='left'
)
atividades['teve_avaliacao'] = atividades['teve_avaliacao'].fillna(0).astype(int)
atividades['com_avaliacao'] = atividades['teve_avaliacao'].apply(lambda x: 'Sim' if x > 0 else 'Não')
atividades['qtd_os_total'] = atividades['qtd_os'] + atividades['teve_avaliacao']

# Mês/Ano
atividades['mes_ano'] = pd.to_datetime(atividades['data_atividade']).dt.to_period('M')

print(f"\n{'='*80}")
print(f"RESUMO GERAL")
print(f"{'='*80}")
print(f"Total de OS únicas da Qualidade (QLW): {OS_QLW_unico['cod_os'].nunique()}")
print(f"Total de ATIVIDADES identificadas:     {len(atividades)}")
print(f"OS de Avaliação de Equipe (complementar): {OS_avaliacoes['cod_os'].nunique()}")
print(f"\nTipos de atividade encontrados:")
for tipo, qtd in atividades['tipo_atividade'].value_counts().items():
    cod = atividades[atividades['tipo_atividade'] == tipo]['cod_esquema'].iloc[0]
    print(f"  {cod:20s} │ {tipo:50s} │ {qtd} atividades")

# =============================================================================
# CÉLULA 4 - TABELAS SEPARADAS POR TIPO DE ATIVIDADE
# =============================================================================

print(f"\n{'='*80}")
print(f"DETALHAMENTO POR TIPO DE ATIVIDADE")
print(f"{'='*80}")

for tipo in atividades['tipo_atividade'].value_counts().index:
    df_tipo = atividades[atividades['tipo_atividade'] == tipo]
    cod = df_tipo['cod_esquema'].iloc[0]
    
    resumo = df_tipo.groupby('grupo_equipe').agg(
        atividades=('aerogerador', 'count'),
        os_total=('qtd_os_total', 'sum'),
        aerogeradores=('aerogerador', 'nunique'),
        parques=('parque', 'nunique'),
        com_avaliacao=('com_avaliacao', lambda x: (x == 'Sim').sum())
    ).reset_index()
    
    resumo.columns = ['Regional', 'Atividades', 'Total OS', 
                       'WTGs Distintos', 'Parques', 'Com Avaliação']
    
    print(f"\n┌{'─'*62}┐")
    print(f"│ [{cod}] {tipo:<{60-len(cod)-4}s} │")
    print(f"│ Total: {len(df_tipo)} atividades | {df_tipo['qtd_os_total'].sum()} OS{' '*(43-len(str(len(df_tipo)))-len(str(df_tipo['qtd_os_total'].sum())))}│")
    print(f"└{'─'*62}┘")
    print(resumo.to_string(index=False))

# =============================================================================
# CÉLULA 5 - TABELA PIVOT: ATIVIDADES POR TIPO × REGIONAL
# =============================================================================

pivot_table = atividades.pivot_table(
    index='tipo_atividade', 
    columns='grupo_equipe', 
    values='aerogerador', 
    aggfunc='count', 
    fill_value=0, 
    margins=True, 
    margins_name='TOTAL'
)

print(f"\n{'='*80}")
print(f"TABELA CRUZADA: ATIVIDADES x REGIONAL")
print(f"{'='*80}")
print(pivot_table.to_string())

# =============================================================================
# CÉLULA 6 - RESUMO MENSAL POR TIPO
# =============================================================================

resumo_mensal = atividades.groupby(['tipo_atividade', 'grupo_equipe', 'mes_ano']).agg(
    atividades=('aerogerador', 'count'),
    os_total=('qtd_os_total', 'sum'),
    aerogeradores=('aerogerador', 'nunique')
).reset_index()

resumo_mensal.columns = ['Tipo Atividade', 'Regional', 'Mês/Ano', 
                          'Atividades', 'OS', 'WTGs']

print(f"\n{'='*80}")
print(f"EVOLUÇÃO MENSAL POR TIPO DE ATIVIDADE")
print(f"{'='*80}")

for tipo in resumo_mensal['Tipo Atividade'].unique():
    df_t = resumo_mensal[resumo_mensal['Tipo Atividade'] == tipo]
    print(f"\n── {tipo} ──")
    print(df_t[['Regional', 'Mês/Ano', 'Atividades', 'OS', 'WTGs']].to_string(index=False))

# =============================================================================
# CÉLULA 7 - VISUALIZAÇÕES GRÁFICAS
# =============================================================================

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.labelsize': 11,
    'figure.facecolor': '#f8f9fa',
    'axes.facecolor': '#ffffff',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
})

CORES_REGIONAL = {
    'AGD': '#2196F3',
    'CE':  '#FF9800',
    'BJS': '#4CAF50',
    'OUTROS': '#9E9E9E'
}

# Gerar paleta de cores dinâmica para os tipos de atividade
tipos_unicos = sorted(atividades['tipo_atividade'].unique())
cmap = cm.get_cmap('tab20', len(tipos_unicos))
CORES_TIPO = {tipo: cmap(i) for i, tipo in enumerate(tipos_unicos)}

# --- GRÁFICO 1: Barras por Regional, empilhadas por Tipo ---
fig, ax = plt.subplots(figsize=(12, 6))

pivot_plot = atividades.pivot_table(
    index='grupo_equipe', 
    columns='tipo_atividade', 
    values='aerogerador', 
    aggfunc='count', 
    fill_value=0
)

cores_barras = [CORES_TIPO.get(c, '#78909C') for c in pivot_plot.columns]
pivot_plot.plot(kind='bar', stacked=True, ax=ax, color=cores_barras, 
                edgecolor='white', linewidth=0.5)

for i, regional in enumerate(pivot_plot.index):
    total = pivot_plot.loc[regional].sum()
    ax.annotate(f'{int(total)}', xy=(i, total), 
                xytext=(0, 5), textcoords="offset points",
                ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_xlabel('Regional')
ax.set_ylabel('Quantidade de Atividades')
ax.set_title('Atividades por Regional — Separadas por Tipo')
ax.legend(title='Tipo de Atividade', bbox_to_anchor=(1.02, 1), 
          loc='upper left', fontsize=7)
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('grafico_atividades_por_tipo_regional.png', dpi=150, bbox_inches='tight')
plt.show()

# --- GRÁFICO 2: Evolução mensal - um subplot para cada tipo ---
n_tipos = len(tipos_unicos)
n_cols = 2
n_rows = int(np.ceil(n_tipos / n_cols))

fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4 * n_rows), squeeze=False)

for idx, tipo in enumerate(tipos_unicos):
    row, col = divmod(idx, n_cols)
    ax = axes[row][col]
    
    df_mes = resumo_mensal[resumo_mensal['Tipo Atividade'] == tipo]
    
    for regional in sorted(df_mes['Regional'].unique()):
        dados = df_mes[df_mes['Regional'] == regional]
        cor = CORES_REGIONAL.get(regional, '#9E9E9E')
        ax.plot(dados['Mês/Ano'].astype(str), dados['Atividades'], 
                marker='o', linewidth=2, markersize=5, label=regional, color=cor)
        
        for _, rd in dados.iterrows():
            ax.annotate(str(rd['Atividades']), 
                        (str(rd['Mês/Ano']), rd['Atividades']),
                        textcoords="offset points", xytext=(0, 6), 
                        ha='center', fontsize=7, fontweight='bold', color=cor)
    
    ax.set_title(tipo, fontsize=10, fontweight='bold')
    ax.set_ylabel('Atividades')
    ax.legend(fontsize=7)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

for idx in range(n_tipos, n_rows * n_cols):
    row, col = divmod(idx, n_cols)
    axes[row][col].set_visible(False)

fig.suptitle('Evolução Mensal por Tipo de Atividade', fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('grafico_evolucao_mensal_por_tipo.png', dpi=150, bbox_inches='tight')
plt.show()

# --- GRÁFICO 3: Barras horizontais - Total por Tipo ---
fig, ax = plt.subplots(figsize=(12, max(5, n_tipos * 0.6)))

tipo_counts = atividades['tipo_atividade'].value_counts().sort_values()
cores_h = [CORES_TIPO.get(t, '#78909C') for t in tipo_counts.index]

bars = ax.barh(tipo_counts.index, tipo_counts.values, color=cores_h, 
               edgecolor='white', linewidth=0.8, height=0.6)

for bar in bars:
    w = bar.get_width()
    ax.annotate(f'{int(w)} atividades', 
                xy=(w, bar.get_y() + bar.get_height() / 2),
                xytext=(5, 0), textcoords="offset points", 
                ha='left', va='center', fontsize=9, fontweight='bold')

ax.set_xlabel('Quantidade de Atividades')
ax.set_title('Total de Atividades por Tipo')
ax.set_xlim(0, tipo_counts.max() * 1.35)
plt.tight_layout()
plt.savefig('grafico_total_por_tipo.png', dpi=150, bbox_inches='tight')
plt.show()

# --- GRÁFICO 4: Por Parque, empilhado por tipo ---
fig, ax = plt.subplots(figsize=(12, 8))

pivot_parque = atividades.pivot_table(
    index='parque', columns='tipo_atividade', 
    values='aerogerador', aggfunc='count', fill_value=0
)
pivot_parque = pivot_parque.loc[pivot_parque.sum(axis=1).sort_values().index]

cores_p = [CORES_TIPO.get(c, '#78909C') for c in pivot_parque.columns]
pivot_parque.plot(kind='barh', stacked=True, ax=ax, color=cores_p,
                  edgecolor='white', linewidth=0.5)

for i, parque in enumerate(pivot_parque.index):
    total = pivot_parque.loc[parque].sum()
    ax.annotate(f'{int(total)}', xy=(total, i), 
                xytext=(5, 0), textcoords="offset points",
                ha='left', va='center', fontsize=9, fontweight='bold')

ax.set_xlabel('Quantidade de Atividades')
ax.set_ylabel('Parque Eólico')
ax.set_title('Atividades por Parque — Separadas por Tipo')
ax.legend(title='Tipo', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7)
plt.tight_layout()
plt.savefig('grafico_atividades_parque_tipo.png', dpi=150, bbox_inches='tight')
plt.show()

# =============================================================================
# CÉLULA 8 - EXPORTAR RELATÓRIO EXCEL
# =============================================================================

atividades_export = atividades[[
    'grupo_equipe', 'cod_esquema', 'tipo_atividade', 'data_atividade', 
    'aerogerador', 'parque', 'qtd_os', 'qtd_os_total', 'componentes', 
    'com_avaliacao', 'inicio', 'fim'
]].copy()

atividades_export.columns = [
    'Regional', 'Cód. Esquema', 'Tipo de Atividade', 'Data', 'Aerogerador', 
    'Parque', 'OS Componentes', 'OS Total (c/ Avaliação)', 
    'Componentes Inspecionados', 'Com Avaliação', 'Início', 'Fim'
]

with pd.ExcelWriter('relatorio_atividades_qualidade.xlsx', engine='openpyxl') as writer:
    
    # Resumo geral (pivot)
    pivot_table.to_excel(writer, sheet_name='Resumo Geral')
    
    # Todas as atividades
    atividades_export.sort_values(['Tipo de Atividade', 'Data', 'Regional']).to_excel(
        writer, sheet_name='Todas Atividades', index=False
    )
    
    # Uma aba para CADA tipo de atividade
    for tipo in sorted(atividades_export['Tipo de Atividade'].unique()):
        nome_aba = re.sub(r'[\\/*?:\[\]<>]', '', tipo)[:31]  # Remove caracteres inválidos e limita a 31
        df_tipo = atividades_export[atividades_export['Tipo de Atividade'] == tipo]
        df_tipo.sort_values('Data').to_excel(writer, sheet_name=nome_aba, index=False)
    
    # Resumo mensal
    resumo_mensal.to_excel(writer, sheet_name='Resumo Mensal', index=False)

print(f"\n{'='*80}")
print(f"✅ RELATÓRIO EXPORTADO: relatorio_atividades_qualidade.xlsx")
print(f"{'='*80}")
print(f"  Total de atividades: {len(atividades_export)}")
print(f"  Total de OS:         {atividades_export['OS Total (c/ Avaliação)'].sum()}")
print(f"\n  Abas criadas:")
print(f"    • Resumo Geral (tabela cruzada)")
print(f"    • Todas Atividades (lista completa)")
for tipo in sorted(atividades_export['Tipo de Atividade'].unique()):
    qtd = len(atividades_export[atividades_export['Tipo de Atividade'] == tipo])
    print(f"    • {tipo[:31]} ({qtd} atividades)")
print(f"    • Resumo Mensal")
