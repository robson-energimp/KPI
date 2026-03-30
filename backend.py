# =============================================================================
# BACKEND - Módulo de dados para Relatório Semanal de Qualidade
# =============================================================================
# Funções de conexão ao EQM, processamento de OS, e gestão de PCM.
# =============================================================================

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

import pandas as pd
import numpy as np
import datetime
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =============================================================================
DB_CONFIG = {
    'database': 'DB_EQM_BI_ENERGIMP',
    'user': 'bi_energimp',
    'password': 'C53BVUYFHCXJD8LUXE5UJYJ8',
    'host': '10.51.1.150',
    'port': 5432
}

# =============================================================================
# MAPEAMENTO DE PARQUES E REGIONAIS
# =============================================================================
PARQUES_POR_REGIONAL = {
    'AGD': ['AMP', 'AQB', 'CAS', 'CBO', 'CRA', 'SAL'],
    'BJS': ['BJS', 'PUL', 'RDO', 'STO'],
    'CE':  ['BUR', 'CAJ', 'COQ', 'MOR', 'QXB'],
}

PARQUES_INFO = {
    'AMP': {'qtd_maq': 15, 'regional': 'AGD'}, 'AQB': {'qtd_maq': 20, 'regional': 'AGD'},
    'BJS': {'qtd_maq': 20, 'regional': 'BJS'}, 'BUR': {'qtd_maq': 20, 'regional': 'CE'},
    'CAJ': {'qtd_maq': 20, 'regional': 'CE'},  'CAS': {'qtd_maq': 4,  'regional': 'AGD'},
    'CBO': {'qtd_maq': 7,  'regional': 'AGD'}, 'COQ': {'qtd_maq': 18, 'regional': 'CE'},
    'CRA': {'qtd_maq': 20, 'regional': 'AGD'}, 'MOR': {'qtd_maq': 19, 'regional': 'CE'},
    'PUL': {'qtd_maq': 20, 'regional': 'BJS'}, 'QXB': {'qtd_maq': 17, 'regional': 'CE'},
    'RDO': {'qtd_maq': 20, 'regional': 'BJS'}, 'SAL': {'qtd_maq': 20, 'regional': 'AGD'},
    'STO': {'qtd_maq': 2,  'regional': 'BJS'},
}

TODOS_PARQUES = sorted(PARQUES_INFO.keys())

AUDITORIA_KEYWORDS = ['AUDITORIA']

CORES_REGIONAL = {
    'AGD': '#1565C0',
    'CE':  '#E65100',
    'BJS': '#2E7D32',
    'OUTROS': '#757575'
}

TIPOS_ATIVIDADE_PADRAO = [
    'INSPEÇÃO VISUAL INTERNA (WTG)',
    'INSPEÇÃO VISUAL EXTERNA (WTG)',
    'MANUTENÇÃO PREVENTIVA',
    'AUDITORIA DE FERRAMENTAS',
    'AVALIAÇÃO DE EQUIPE',
    'OUTRO',
]


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def equipe_grupo(cod_equipe):
    """Mapeia código de equipe para grupo regional."""
    cod = str(cod_equipe).upper()
    if 'CE' in cod:
        return 'CE'
    elif 'BJS' in cod:
        return 'BJS'
    elif 'AGD' in cod:
        return 'AGD'
    else:
        return 'OUTROS'


def obter_semana_atual():
    """Retorna informações da semana atual."""
    hoje = datetime.date.today()
    semana_num = hoje.isocalendar()[1]
    inicio = hoje - datetime.timedelta(days=hoje.weekday())
    fim = inicio + datetime.timedelta(days=6)
    return {
        'semana_num': semana_num,
        'ano': hoje.year,
        'inicio': inicio,
        'fim': fim,
        'periodo': f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}",
        'label': f"{hoje.year}-S{str(semana_num).zfill(2)}"
    }


def obter_tipos_atividade():
    """Retorna tipos de atividade conhecidos (do Excel ou padrão)."""
    filepath = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.xlsx')
    if os.path.exists(filepath):
        try:
            df = pd.read_excel(filepath)
            return sorted(df['desc_esquema'].dropna().unique().tolist())
        except Exception:
            pass
    return TIPOS_ATIVIDADE_PADRAO


# =============================================================================
# CONEXÃO COM BANCO DE DADOS EQM
# =============================================================================
def testar_conexao():
    """Testa conexão com o banco EQM. Retorna (sucesso, mensagem)."""
    if not HAS_PSYCOPG2:
        return False, "Driver psycopg2 não disponível (ambiente cloud)"
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=5)
        conn.close()
        return True, "Conexão estabelecida com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"


def consultar_eqm(sql):
    """Executa consulta SQL no banco EQM."""
    if not HAS_PSYCOPG2:
        raise RuntimeError("Driver psycopg2 não disponível (ambiente cloud)")
    conn = psycopg2.connect(**DB_CONFIG, connect_timeout=10)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        resultado = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        return pd.DataFrame(resultado, columns=colunas) if resultado else pd.DataFrame()
    finally:
        conn.close()


def buscar_os_wtg(data_inicio, data_fim):
    """Busca OS de WTG executadas no período."""
    t1 = data_inicio.strftime('%Y-%m-%d') if not isinstance(data_inicio, str) else data_inicio
    t2 = data_fim.strftime('%Y-%m-%d') if not isinstance(data_fim, str) else data_fim

    sql = f"""SELECT
        C.cod_ss, C.desc_numero_ss, A.cod_os, A.desc_numero_os,
        A.cod_equipe, A.cod_especie, A.cod_esquema, F.desc_esquema,
        E.desc_especie,
        right(A.cod_instalacao, 3) || '-' || right(D.desc_localizacao, 2) as Aerogerador,
        A.data_inicio_exec, A.data_fim_exec, A.desc_defeito,
        A.desc_causa_primaria, A.desc_origem, A.text_observacao,
        B.desc_carac, B.resposta
    FROM "EQM_BI_ENERGIMP".bi_osexec A
    LEFT JOIN "EQM_BI_ENERGIMP".bi_osexec_carac B ON A.cod_os = B.cod_os
    LEFT JOIN "EQM_BI_ENERGIMP".bi_ss C ON A.cod_os = C.cod_os
    LEFT JOIN "EQM_BI_ENERGIMP".bi_especie E ON E.cod_especie = A.cod_especie
    LEFT JOIN "EQM_BI_ENERGIMP".bi_esquema F ON F.cod_esquema = A.cod_esquema
    LEFT JOIN "EQM_BI_ENERGIMP".bi_ativo D ON A.cod_ativo = D.cod_ativo
    WHERE A.data_inicio_exec >= '{t1}' AND A.data_inicio_exec <= '{t2}'
    AND A.os_fechada = 'Sim' AND A.desc_estado = 'EXECUTADA'
    ORDER BY A.data_criacao"""

    return consultar_eqm(sql)


# =============================================================================
# PROCESSAMENTO DE DADOS
# =============================================================================
def processar_dados_qualidade(df_raw):
    """Processa OS brutas em tabela de atividades de qualidade."""
    os_qlw = df_raw[df_raw['desc_numero_os'].str.contains('QLW', na=False)].copy()
    os_qlw['grupo_equipe'] = os_qlw['cod_equipe'].apply(equipe_grupo)

    tabela = os_qlw.groupby(
        ['grupo_equipe', 'data_inicio_exec', 'data_fim_exec', 'aerogerador', 'desc_especie', 'desc_esquema']
    ).size().reset_index(name='quantidade')

    return tabela


def processar_atividades(df):
    """Processa dados em atividades semanais (turbinas e auditorias)."""
    df = df.copy()
    df['data_inicio_exec'] = pd.to_datetime(df['data_inicio_exec'])
    if 'data_fim_exec' in df.columns:
        df['data_fim_exec'] = pd.to_datetime(df['data_fim_exec'])

    df['parque'] = df['aerogerador'].str[:3]
    df['semana_num'] = df['data_inicio_exec'].dt.isocalendar().week.astype(int)
    df['ano_semana'] = df['data_inicio_exec'].dt.strftime('%Y') + '-S' + df['semana_num'].astype(str).str.zfill(2)
    df['inicio_semana'] = df['data_inicio_exec'] - pd.to_timedelta(df['data_inicio_exec'].dt.dayofweek, unit='D')
    df['fim_semana'] = df['inicio_semana'] + pd.Timedelta(days=6)
    df['periodo_semana'] = df['inicio_semana'].dt.strftime('%d/%m') + ' a ' + df['fim_semana'].dt.strftime('%d/%m/%Y')

    def eh_auditoria(desc):
        if pd.isna(desc):
            return False
        return any(kw in str(desc).upper() for kw in AUDITORIA_KEYWORDS)

    df['eh_auditoria'] = df['desc_esquema'].apply(eh_auditoria)
    df['eh_avaliacao'] = df['desc_esquema'].str.upper().str.contains('AVALIA', na=False)

    df_turbinas = df[~df['eh_auditoria'] & ~df['eh_avaliacao']].copy()
    df_auditorias = df[df['eh_auditoria']].copy()

    # Agrupar atividades em turbinas
    if not df_turbinas.empty:
        ativ_turbinas = df_turbinas.groupby(
            ['grupo_equipe', 'data_inicio_exec', 'aerogerador', 'parque',
             'desc_esquema', 'ano_semana', 'semana_num', 'periodo_semana']
        ).agg(
            qtd_os=('quantidade', 'sum'),
            componentes=('desc_especie', lambda x: ', '.join(sorted(x.unique())))
        ).reset_index()
    else:
        ativ_turbinas = pd.DataFrame()

    # Agrupar auditorias
    if not df_auditorias.empty:
        ativ_auditorias = df_auditorias.groupby(
            ['grupo_equipe', 'ano_semana', 'semana_num', 'periodo_semana']
        ).agg(
            ferramentas_auditadas=('aerogerador', 'nunique'),
            qtd_os=('quantidade', 'sum'),
            desc_esquema=('desc_esquema', 'first')
        ).reset_index()
    else:
        ativ_auditorias = pd.DataFrame()

    return ativ_turbinas, ativ_auditorias


# =============================================================================
# GESTÃO DE FICHEIROS EXCEL
# =============================================================================
def carregar_dados_excel(filepath=None):
    """Carrega dados do Excel existente."""
    if filepath is None:
        filepath = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.xlsx')
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_excel(filepath)
    except Exception:
        return None


def salvar_dados_excel(df, filepath=None):
    """Salva dados no Excel."""
    if filepath is None:
        filepath = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.xlsx')
    df.to_excel(filepath, index=False)
    return filepath


# =============================================================================
# GESTÃO DE ATIVIDADES PCM (Planejadas)
# =============================================================================
PCM_FILE = os.path.join(BASE_DIR, 'pcm_atividades_semana.json')


def carregar_pcm():
    """Carrega atividades planejadas do arquivo JSON."""
    if os.path.exists(PCM_FILE):
        try:
            with open(PCM_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def salvar_pcm(atividades):
    """Salva atividades planejadas no arquivo JSON."""
    with open(PCM_FILE, 'w', encoding='utf-8') as f:
        json.dump(atividades, f, ensure_ascii=False, indent=2, default=str)


def adicionar_atividade_pcm(regional, parque, aerogerador, tipo, data_prevista, responsavel, observacoes):
    """Adiciona uma atividade planejada."""
    atividades = carregar_pcm()
    atividades.append({
        'id': len(atividades) + 1,
        'regional': regional,
        'parque': parque,
        'aerogerador': aerogerador,
        'tipo_atividade': tipo,
        'data_prevista': str(data_prevista),
        'responsavel': responsavel,
        'observacoes': observacoes,
        'criado_em': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    salvar_pcm(atividades)
    return atividades


def remover_atividade_pcm(indice):
    """Remove atividade por índice."""
    atividades = carregar_pcm()
    if 0 <= indice < len(atividades):
        atividades.pop(indice)
        salvar_pcm(atividades)
    return atividades


def limpar_pcm():
    """Limpa todas as atividades planejadas."""
    salvar_pcm([])
    return []


def pipeline_completo(data_inicio=None, data_fim=None):
    """
    Executa o pipeline completo:
    1. Busca dados do EQM
    2. Processa atividades
    3. Salva Excel
    Retorna (df_dados, ativ_turbinas, ativ_auditorias, mensagem)
    """
    if data_inicio is None:
        data_inicio = pd.to_datetime('2026-01-01')
    if data_fim is None:
        data_fim = datetime.datetime.today()

    try:
        # 1. Buscar dados do banco
        df_raw = buscar_os_wtg(data_inicio, data_fim)
        if df_raw.empty:
            return None, None, None, "Nenhum dado retornado do banco."

        # 2. Processar dados de qualidade
        df_quality = processar_dados_qualidade(df_raw)
        if df_quality.empty:
            return None, None, None, "Nenhuma OS de qualidade (QLW) encontrada."

        # 3. Salvar Excel
        salvar_dados_excel(df_quality)

        # 4. Processar atividades
        ativ_turbinas, ativ_auditorias = processar_atividades(df_quality)

        msg = (f"✅ {len(df_quality)} registros processados. "
               f"Turbinas: {len(ativ_turbinas)}, Auditorias: {len(ativ_auditorias)}")

        return df_quality, ativ_turbinas, ativ_auditorias, msg

    except Exception as e:
        return None, None, None, f"❌ Erro: {str(e)}"
