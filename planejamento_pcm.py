# =============================================================================
# PLANEJAMENTO_PCM.PY - Módulo de Planejamento Semanal via PCM
# =============================================================================
# Lê os arquivos de programação da pasta Atividades_PCM, filtra equipes QLW,
# e gerencia tarefas de acompanhamento com histórico.
# =============================================================================

import pandas as pd
import numpy as np
import datetime
import os
import json
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_PCM = os.path.join(BASE_DIR, 'Atividades_PCM')
HISTORICO_FILE = os.path.join(PASTA_PCM, 'historico_planejamento_pcm.xlsx')
TASKS_FILE = os.path.join(PASTA_PCM, 'tasks_planejamento.json')

# Equipes de qualidade a filtrar
EQUIPES_QLW = ['QLW-CE', 'QLW-BJS', 'QLW-AGD']

# Motivos padrão para não cumprimento do planejamento
MOTIVOS_NAO_CUMPRIMENTO = [
    'Condições Climáticas',
    'Falta de Material/Peça',
    'Máquina Indisponível',
    'Equipe Redirecionada',
    'Problema de Acesso',
    'Manutenção Corretiva Prioritária',
    'Falta de Transporte',
    'Treinamento/Reunião',
    'Problema de Segurança',
    'Outro',
]

# Mapeamento de colunas por formato de arquivo
# Os arquivos podem ter diferentes nomes de colunas e posições de header
COLUMN_MAPPINGS = {
    'equipe':       ['Equipe'],
    'esquema':      ['Esquema'],
    'ativo':        ['Ativo'],
    'familia':      ['Família', 'Familia'],
    'complemento':  ['Complemento', 'Complemento Loc'],
    'ordem':        ['Ordem', 'OS'],
    'dt_inicio':    ['Dt. Início', 'Início Prog.', 'Dt. Inicio'],
    'dt_termino':   ['Dt. Término', 'Término Prog.', 'Dt. Termino'],
    'responsavel':  ['Responsável', 'Responsápel'],
    'observacao':   ['Observação', 'Observaçao'],
    'semana':       ['Nº Sem', 'N° Sem', 'Semana'],
    'complexo':     ['Complexo', 'Área', 'Area'],
    'localizacao':  ['Localização', 'Localizacao'],
    'status_os':    ['Status OS', 'Estado SI'],
    'plano':        ['Descrição Plano', 'Plano'],
}


def _find_column(df, key):
    """Encontra a coluna no DataFrame baseado nos possíveis nomes."""
    possible_names = COLUMN_MAPPINGS.get(key, [])
    for name in possible_names:
        # Busca exata
        if name in df.columns:
            return name
        # Busca case-insensitive e com normalização de acentos
        for col in df.columns:
            col_clean = str(col).strip()
            if col_clean.lower() == name.lower():
                return col
            # Comparação sem acentos (simplificada)
            col_ascii = col_clean.encode('ascii', 'ignore').decode('ascii').lower()
            name_ascii = name.encode('ascii', 'ignore').decode('ascii').lower()
            if col_ascii == name_ascii:
                return col
    return None


def _detect_header_row(filepath, sheet_name):
    """Detecta a linha do header procurando a coluna 'Equipe'."""
    for header_row in range(5):
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name,
                              header=header_row, nrows=3)
            for col in df.columns:
                if 'equipe' in str(col).lower().strip():
                    return header_row
        except Exception:
            continue
    return 0  # fallback


def _extract_regional_from_equipe(equipe_str):
    """Extrai o código regional do nome da equipe (ex: QLW-CE -> CE)."""
    if pd.isna(equipe_str):
        return ''
    parts = str(equipe_str).split('-')
    if len(parts) >= 2:
        return parts[-1].strip().upper()
    return str(equipe_str).strip().upper()


def _extract_aerogerador_from_complemento(complemento):
    """Extrai identificação do aerogerador do campo Complemento.
    Ex: 'SAL 17-C2' -> 'SAL-17', 'COQ 08-C2' -> 'COQ-08'
    """
    if pd.isna(complemento):
        return ''
    comp = str(complemento).strip()
    # Padrão: 'XXX NN-CY' ou 'XXX-NN'
    parts = comp.split()
    if len(parts) >= 2:
        parque = parts[0]
        num = parts[1].split('-')[0]
        return f"{parque}-{num}"
    return comp


def ler_programacao_pcm(pasta=None):
    """
    Lê todos os arquivos Excel da pasta Atividades_PCM,
    busca a aba 'Base de Envio' ou 'Programação',
    filtra equipes QLW e retorna DataFrame unificado.

    Retorna: DataFrame com colunas padronizadas ou DataFrame vazio.
    """
    if pasta is None:
        pasta = PASTA_PCM

    if not os.path.exists(pasta):
        return pd.DataFrame()

    all_data = []

    for arquivo in os.listdir(pasta):
        if not arquivo.endswith(('.xlsx', '.xls')):
            continue
        if arquivo.startswith('~$'):  # arquivos temporários do Excel
            continue
        if 'historico' in arquivo.lower() or 'tasks' in arquivo.lower():
            continue

        filepath = os.path.join(pasta, arquivo)

        try:
            xls = pd.ExcelFile(filepath)
        except Exception:
            continue

        # Procurar a aba correta
        target_sheet = None
        for sn in xls.sheet_names:
            sn_lower = sn.lower()
            if 'base' in sn_lower and 'envio' in sn_lower:
                target_sheet = sn
                break
            elif 'programa' in sn_lower:
                target_sheet = sn
                # Não quebra aqui, pois 'Base de Envio' tem prioridade

        if target_sheet is None:
            # Usa a primeira aba como fallback
            target_sheet = xls.sheet_names[0]

        # Detectar header
        header_row = _detect_header_row(filepath, target_sheet)

        try:
            df = pd.read_excel(filepath, sheet_name=target_sheet,
                              header=header_row)
        except Exception:
            continue

        # Encontrar coluna Equipe
        col_equipe = _find_column(df, 'equipe')
        if col_equipe is None:
            continue

        # Filtrar equipes QLW
        mask_qlw = df[col_equipe].astype(str).str.upper().str.strip().isin(
            [e.upper() for e in EQUIPES_QLW]
        )
        df_qlw = df[mask_qlw].copy()

        if df_qlw.empty:
            continue

        # Mapear colunas para nomes padronizados
        col_map = {}
        for key in COLUMN_MAPPINGS:
            found = _find_column(df_qlw, key)
            if found:
                col_map[found] = key

        df_qlw = df_qlw.rename(columns=col_map)

        # Adicionar metadados
        df_qlw['arquivo_origem'] = arquivo

        # Extrair regional da equipe
        if 'equipe' in df_qlw.columns:
            df_qlw['regional'] = df_qlw['equipe'].apply(
                _extract_regional_from_equipe
            )

        # Extrair aerogerador do complemento
        if 'complemento' in df_qlw.columns:
            df_qlw['aerogerador'] = df_qlw['complemento'].apply(
                _extract_aerogerador_from_complemento
            )
        elif 'localizacao' in df_qlw.columns:
            df_qlw['aerogerador'] = df_qlw['localizacao'].astype(str)

        all_data.append(df_qlw)

    if not all_data:
        return pd.DataFrame()

    # Unificar DataFrames
    df_unificado = pd.concat(all_data, ignore_index=True)

    # Selecionar e padronizar colunas de interesse
    colunas_finais = [
        'regional', 'equipe', 'aerogerador', 'complemento',
        'esquema', 'ativo', 'familia', 'plano',
        'dt_inicio', 'dt_termino', 'responsavel',
        'semana', 'observacao', 'status_os', 'arquivo_origem'
    ]
    colunas_existentes = [c for c in colunas_finais if c in df_unificado.columns]
    df_resultado = df_unificado[colunas_existentes].copy()

    return df_resultado


def agrupar_atividades_pcm(df_pcm):
    """
    Agrupa os dados do PCM por atividade.
    Uma atividade pode ter várias OS (definidas pelo Ativo).
    Agrupa por: Regional + Aerogerador + Esquema.

    Retorna DataFrame com atividades agrupadas.
    """
    if df_pcm.empty:
        return pd.DataFrame()

    # Garantir que as colunas existam
    cols_group = []
    for c in ['regional', 'equipe', 'aerogerador', 'complemento', 'esquema']:
        if c in df_pcm.columns:
            cols_group.append(c)

    if not cols_group or 'esquema' not in cols_group:
        return df_pcm

    agg_dict = {}
    if 'ativo' in df_pcm.columns:
        agg_dict['ativo'] = lambda x: ', '.join(sorted(x.dropna().unique()))
    if 'familia' in df_pcm.columns:
        agg_dict['familia'] = lambda x: ', '.join(sorted(x.dropna().unique()))
    if 'dt_inicio' in df_pcm.columns:
        agg_dict['dt_inicio'] = 'first'
    if 'dt_termino' in df_pcm.columns:
        agg_dict['dt_termino'] = 'first'
    if 'responsavel' in df_pcm.columns:
        agg_dict['responsavel'] = 'first'
    if 'semana' in df_pcm.columns:
        agg_dict['semana'] = 'first'
    if 'plano' in df_pcm.columns:
        agg_dict['plano'] = 'first'
    if 'arquivo_origem' in df_pcm.columns:
        agg_dict['arquivo_origem'] = 'first'

    # Contar OS por atividade
    agg_dict['_count'] = ('esquema', 'count')

    # Construir agregação separadamente para evitar conflito
    if agg_dict:
        # Montar dict sem _count
        real_agg = {k: v for k, v in agg_dict.items() if k != '_count'}
        df_grouped = df_pcm.groupby(cols_group, dropna=False).agg(**{
            k: (k, v) if isinstance(v, str) else (k, v)
            for k, v in real_agg.items()
        }).reset_index()
        # Contar OS
        counts = df_pcm.groupby(cols_group, dropna=False).size().reset_index(
            name='qtd_os'
        )
        df_grouped = df_grouped.merge(counts, on=cols_group, how='left')
    else:
        df_grouped = df_pcm[cols_group].drop_duplicates().reset_index(drop=True)
        df_grouped['qtd_os'] = 1

    return df_grouped


# =============================================================================
# GESTÃO DE TASKS (Tarefas com status e observações)
# =============================================================================
def carregar_tasks():
    """Carrega as tasks de planejamento do JSON."""
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def salvar_tasks(tasks):
    """Salva tasks de planejamento no JSON."""
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2, default=str)


def criar_tasks_do_pcm(df_pcm, semana_label, sobrescrever=False):
    """
    Cria tasks de acompanhamento a partir do DataFrame do PCM.
    Cada linha gera uma task com status pendente.

    Args:
        df_pcm: DataFrame com atividades PCM
        semana_label: Ex: 'S17' ou '2026-S17'
        sobrescrever: Se True, substitui tasks existentes da mesma semana
    """
    tasks_atuais = carregar_tasks()

    if sobrescrever:
        # Remove tasks da mesma semana
        tasks_atuais = [t for t in tasks_atuais if t.get('semana') != semana_label]

    novas_tasks = []
    for idx, row in df_pcm.iterrows():
        task = {
            'id': f"{semana_label}_{idx}_{datetime.datetime.now().strftime('%H%M%S')}",
            'semana': semana_label,
            'regional': str(row.get('regional', '')),
            'equipe': str(row.get('equipe', '')),
            'aerogerador': str(row.get('aerogerador', '')),
            'complemento': str(row.get('complemento', '')),
            'atividade': str(row.get('esquema', '')),
            'familia': str(row.get('familia', '')),
            'ativo': str(row.get('ativo', '')),
            'responsavel': str(row.get('responsavel', '')),
            'dt_inicio': str(row.get('dt_inicio', '')),
            'dt_termino': str(row.get('dt_termino', '')),
            'concluido': False,
            'motivo_nao_cumprimento': '',
            'observacoes': '',
            'atualizado_em': '',
            'criado_em': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        novas_tasks.append(task)

    tasks_atuais.extend(novas_tasks)
    salvar_tasks(tasks_atuais)
    return tasks_atuais


def atualizar_task(task_id, concluido=None, motivo=None, observacoes=None):
    """Atualiza o status de uma task específica."""
    tasks = carregar_tasks()
    for task in tasks:
        if task['id'] == task_id:
            if concluido is not None:
                task['concluido'] = concluido
            if motivo is not None:
                task['motivo_nao_cumprimento'] = motivo
            if observacoes is not None:
                task['observacoes'] = observacoes
            task['atualizado_em'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            break
    salvar_tasks(tasks)
    return tasks


def atualizar_tasks_em_lote(updates):
    """
    Atualiza múltiplas tasks de uma vez.
    updates: lista de dicts com {task_id, concluido, motivo, observacoes}
    """
    tasks = carregar_tasks()
    task_map = {t['id']: t for t in tasks}

    for upd in updates:
        tid = upd.get('task_id')
        if tid in task_map:
            if 'concluido' in upd:
                task_map[tid]['concluido'] = upd['concluido']
            if 'motivo' in upd:
                task_map[tid]['motivo_nao_cumprimento'] = upd['motivo']
            if 'observacoes' in upd:
                task_map[tid]['observacoes'] = upd['observacoes']
            task_map[tid]['atualizado_em'] = datetime.datetime.now().strftime(
                '%Y-%m-%d %H:%M'
            )

    tasks = list(task_map.values())
    salvar_tasks(tasks)
    return tasks


def obter_tasks_semana(semana_label):
    """Retorna tasks de uma semana específica."""
    tasks = carregar_tasks()
    return [t for t in tasks if t.get('semana') == semana_label]


def obter_semanas_disponiveis():
    """Retorna lista de semanas que têm tasks."""
    tasks = carregar_tasks()
    semanas = sorted(set(t.get('semana', '') for t in tasks if t.get('semana')))
    return semanas


def limpar_tasks_semana(semana_label):
    """Remove todas as tasks de uma semana específica."""
    tasks = carregar_tasks()
    tasks = [t for t in tasks if t.get('semana') != semana_label]
    salvar_tasks(tasks)
    return tasks


def adicionar_task_manual(semana_label, regional, equipe, aerogerador,
                          complemento, atividade, familia, responsavel):
    """Adiciona uma task manualmente (sem origem PCM)."""
    tasks = carregar_tasks()
    task = {
        'id': f"{semana_label}_manual_{datetime.datetime.now().strftime('%H%M%S%f')}",
        'semana': semana_label,
        'regional': regional,
        'equipe': equipe,
        'aerogerador': aerogerador,
        'complemento': complemento,
        'atividade': atividade,
        'familia': familia,
        'ativo': '',
        'responsavel': responsavel,
        'dt_inicio': '',
        'dt_termino': '',
        'concluido': False,
        'motivo_nao_cumprimento': '',
        'observacoes': '',
        'atualizado_em': '',
        'criado_em': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'origem': 'manual',
    }
    tasks.append(task)
    salvar_tasks(tasks)
    return tasks


# =============================================================================
# HISTÓRICO EM EXCEL
# =============================================================================
def salvar_historico(tasks=None, filepath=None):
    """
    Salva o estado atual das tasks como histórico em Excel.
    Cada execução adiciona/atualiza os registros da semana correspondente.
    """
    if filepath is None:
        filepath = HISTORICO_FILE

    if tasks is None:
        tasks = carregar_tasks()

    if not tasks:
        return filepath

    df_novo = pd.DataFrame(tasks)

    # Ajustar colunas para apresentação
    col_rename = {
        'semana': 'Semana',
        'regional': 'Regional',
        'equipe': 'Equipe',
        'aerogerador': 'Aerogerador',
        'complemento': 'Complemento',
        'atividade': 'Atividade',
        'familia': 'Família',
        'ativo': 'Ativo',
        'responsavel': 'Responsável',
        'dt_inicio': 'Data Início',
        'dt_termino': 'Data Término',
        'concluido': 'Concluído',
        'motivo_nao_cumprimento': 'Motivo Não Cumprimento',
        'observacoes': 'Observações',
        'atualizado_em': 'Atualizado Em',
        'criado_em': 'Criado Em',
    }
    cols_existentes = {k: v for k, v in col_rename.items() if k in df_novo.columns}
    df_novo = df_novo.rename(columns=cols_existentes)

    # Mapear Concluído para Sim/Não
    if 'Concluído' in df_novo.columns:
        df_novo['Concluído'] = df_novo['Concluído'].map(
            {True: 'Sim', False: 'Não', 'true': 'Sim', 'false': 'Não'}
        ).fillna('Não')

    # Se existe histórico anterior, mesclar
    if os.path.exists(filepath):
        try:
            df_existente = pd.read_excel(filepath)
            # Remover semanas que estão sendo atualizadas
            semanas_novas = df_novo['Semana'].unique()
            df_existente = df_existente[~df_existente['Semana'].isin(semanas_novas)]
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo

    # Selecionar colunas de apresentação
    colunas_export = [
        'Semana', 'Regional', 'Equipe', 'Aerogerador', 'Complemento',
        'Atividade', 'Família', 'Ativo', 'Responsável',
        'Data Início', 'Data Término', 'Concluído',
        'Motivo Não Cumprimento', 'Observações',
        'Atualizado Em', 'Criado Em'
    ]
    colunas_export = [c for c in colunas_export if c in df_final.columns]
    df_final = df_final[colunas_export]

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df_final.to_excel(filepath, index=False)
    return filepath


def carregar_historico(filepath=None):
    """Carrega histórico do Excel."""
    if filepath is None:
        filepath = HISTORICO_FILE
    if not os.path.exists(filepath):
        return pd.DataFrame()
    try:
        return pd.read_excel(filepath)
    except Exception:
        return pd.DataFrame()


def obter_resumo_planejamento(semana_label=None):
    """
    Retorna resumo do planejamento com métricas de aderência.
    Se semana_label é None, retorna para todas as semanas.
    """
    tasks = carregar_tasks()
    if semana_label:
        tasks = [t for t in tasks if t.get('semana') == semana_label]

    if not tasks:
        return {
            'total': 0, 'concluidas': 0, 'pendentes': 0,
            'aderencia': 0, 'por_regional': {}
        }

    total = len(tasks)
    concluidas = sum(1 for t in tasks if t.get('concluido'))
    pendentes = total - concluidas
    aderencia = round(concluidas / total * 100, 1) if total > 0 else 0

    # Por regional
    por_regional = {}
    for t in tasks:
        reg = t.get('regional', 'OUTROS')
        if reg not in por_regional:
            por_regional[reg] = {'total': 0, 'concluidas': 0}
        por_regional[reg]['total'] += 1
        if t.get('concluido'):
            por_regional[reg]['concluidas'] += 1

    for reg in por_regional:
        r = por_regional[reg]
        r['aderencia'] = round(r['concluidas'] / r['total'] * 100, 1) if r['total'] > 0 else 0

    # Motivos de não cumprimento
    motivos = {}
    for t in tasks:
        if not t.get('concluido') and t.get('motivo_nao_cumprimento'):
            m = t['motivo_nao_cumprimento']
            motivos[m] = motivos.get(m, 0) + 1

    return {
        'total': total,
        'concluidas': concluidas,
        'pendentes': pendentes,
        'aderencia': aderencia,
        'por_regional': por_regional,
        'motivos': motivos,
    }
