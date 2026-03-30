# =============================================================================
# ATUALIZAR RELATÓRIO SEMANAL - SCRIPT UM CLIQUE
# =============================================================================
# Este script faz todo o fluxo automaticamente:
#   1. Conecta ao banco EQM e busca dados atualizados
#   2. Gera o Excel Resumo_Atividades_Qualidade_2026.xlsx
#   3. Executa a análise de atividades
#   4. Gera o relatório PDF semanal
#
# Basta rodar toda segunda-feira:
#   python atualizar_relatorio.py
# =============================================================================

import psycopg2
import pandas as pd
import datetime
import os
import sys
import subprocess

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
# Diretório base do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJETO_DIR = os.path.dirname(BASE_DIR)  # Pasta Energimp

# Arquivo de saída
ARQUIVO_EXCEL = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.xlsx')

# Datas dinâmicas: desde 01/01/2026 até HOJE
t_inicial = pd.to_datetime('2026-01-01')
t_final = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

print("=" * 70)
print("ATUALIZAÇÃO DO RELATÓRIO SEMANAL DE QUALIDADE")
print("=" * 70)
print(f"  Data de execução: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
print(f"  Período dos dados: {t_inicial.strftime('%d/%m/%Y')} a {t_final.strftime('%d/%m/%Y')}")
print("=" * 70)

# =============================================================================
# ETAPA 1 - CONSULTA AO BANCO EQM
# =============================================================================
print("\n[1/4] Consultando banco de dados EQM...")

Parques = ['AMP', 'AQB', 'BJS', 'BUR', 'CAJ', 'CAS', 'CBO', 'COQ', 'CRA', 'MOR', 'PUL', 'QXB', 'RDO', 'SAL', 'STO']
Qtd_Maqs = ['15', '20', '20', '20', '20', '4', '7', '18', '20', '19', '20', '17', '20', '20', '2']
Complexo = ['AGD', 'AGD', 'BJS', 'PPG', 'PPG', 'AGD', 'AGD', 'PPG', 'AGD', 'MOR', 'BJS', 'QXB', 'BJS', 'AGD', 'BJS']
Regional = ['Água Doce', 'Água Doce', 'Bom Jardim', 'Ceará', 'Ceará', 'Água Doce', 'Água Doce', 'Ceará',
            'Água Doce', 'Ceará', 'Bom Jardim', 'Ceará', 'Bom Jardim', 'Água Doce', 'Bom Jardim']

Pq_Maq = pd.DataFrame({'Parque': Parques, 'Qtd_Maq': Qtd_Maqs, 'Complexo': Complexo, 'Regional': Regional})
Pq_Maq['Qtd_Maq'] = Pq_Maq['Qtd_Maq'].astype(int)


def consultaEQM(Q1):
    """Executa consulta SQL no banco EQM."""
    connection = psycopg2.connect(
        database="DB_EQM_BI_ENERGIMP",
        user="bi_energimp",
        password="C53BVUYFHCXJD8LUXE5UJYJ8",
        host="10.51.1.150",
        port=5432
    )
    cursor = connection.cursor()
    cursor.execute(Q1)
    resultado = cursor.fetchall()
    colunas = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(resultado)
    if len(df) == 0:
        print('  Consulta retornou sem resultados.')
    else:
        df.columns = colunas
        print(f'  Consulta ok - {len(df)} registros.')
    connection.close()
    return df


def consultaOsWTG(t1, t2):
    """Consulta OS de WTG executadas no período."""
    if not isinstance(t1, str):
        t1 = t1.strftime('%Y-%m-%d')
    if not isinstance(t2, str):
        t2 = t2.strftime('%Y-%m-%d')

    txt = """select \
      C.cod_ss \
    , C.desc_numero_ss \
    , A.cod_os \
    , A.desc_numero_os \
    , A.cod_equipe \
    , A.cod_especie \
    , A.cod_esquema \
    , F.desc_esquema \
    , E.desc_especie \
    , right(A.cod_instalacao, 3) || '-' || right(D.desc_localizacao, 2) as Aerogerador \
    , A.data_inicio_exec \
    , A.data_fim_exec \
    , A.desc_defeito \
    , A.desc_causa_primaria \
    , A.desc_origem \
    , A.text_observacao \
    , B.desc_carac \
    , B.resposta \
    from "EQM_BI_ENERGIMP".bi_osexec A
    left join "EQM_BI_ENERGIMP".bi_osexec_carac B on A.cod_os = B.cod_os
    left join "EQM_BI_ENERGIMP".bi_ss C on A.cod_os = C.cod_os \
    left join "EQM_BI_ENERGIMP".bi_especie E on E.cod_especie = A.cod_especie \
    left join "EQM_BI_ENERGIMP".bi_esquema F on F.cod_esquema = A.cod_esquema \
    left join "EQM_BI_ENERGIMP".bi_ativo D on A.cod_ativo = D.cod_ativo """ \
    + f"where A.data_inicio_exec >= '{t1}' and A.data_inicio_exec <= '{t2}' " \
    + f"and A.os_fechada = 'Sim' and A.desc_estado = 'EXECUTADA' " \
    + "order by A.data_criacao"

    return consultaEQM(txt)


try:
    CondOS_WTG = consultaOsWTG(t_inicial, t_final)
except Exception as e:
    print(f"\n[ERRO] Falha na consulta ao banco: {e}")
    print("Verifique se está conectado à rede/VPN.")
    sys.exit(1)

# =============================================================================
# ETAPA 2 - GERAR EXCEL ATUALIZADO
# =============================================================================
print("\n[2/4] Gerando Excel atualizado...")


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


# Filtrar OS da equipe de Qualidade
OS_QLW = CondOS_WTG[CondOS_WTG['desc_numero_os'].str.contains('QLW', na=False)].copy()
OS_QLW['grupo_equipe'] = OS_QLW['cod_equipe'].apply(equipe_grupo)

# Agrupe e conte
tabela_causas = OS_QLW.groupby(
    ['grupo_equipe', 'data_inicio_exec', 'data_fim_exec', 'aerogerador', 'desc_especie', 'desc_esquema']
).size().reset_index(name='quantidade')

# Salvar Excel
tabela_causas.to_excel(ARQUIVO_EXCEL, index=False)
print(f"  Excel salvo: {ARQUIVO_EXCEL}")
print(f"  Registros: {len(tabela_causas)}")

# =============================================================================
# ETAPA 3 - EXECUTAR ANÁLISE DE ATIVIDADES
# =============================================================================
print("\n[3/4] Executando análise de atividades...")

# Tornar CondOS_WTG acessível para o script de análise
# (o analise_atividades_qualidade.py espera que CondOS_WTG já exista)
script_analise = os.path.join(BASE_DIR, 'analise_atividades_qualidade.py')
if os.path.exists(script_analise):
    # Executar o script de análise no contexto atual
    exec(open(script_analise, encoding='utf-8').read())
    print("  Análise concluída.")
else:
    print(f"  [AVISO] Script de análise não encontrado: {script_analise}")

# =============================================================================
# ETAPA 4 - GERAR RELATÓRIO PDF
# =============================================================================
print("\n[4/4] Gerando relatório PDF...")

script_pdf = os.path.join(BASE_DIR, 'relatorio_semanal_pdf.py')
if os.path.exists(script_pdf):
    # Mudar para o diretório do script para que os caminhos relativos funcionem
    os.chdir(BASE_DIR)
    subprocess.run([sys.executable, script_pdf], check=True)
else:
    print(f"  [AVISO] Script do PDF não encontrado: {script_pdf}")

print("\n" + "=" * 70)
print("✅ ATUALIZAÇÃO COMPLETA!")
print("=" * 70)
print(f"  Período coberto: {t_inicial.strftime('%d/%m/%Y')} a {t_final.strftime('%d/%m/%Y')}")
print(f"  Executado em: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 70)
