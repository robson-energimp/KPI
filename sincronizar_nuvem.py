import os
import sys
import subprocess
import datetime
import psycopg2
import pandas as pd

# =============================================================================
# SINCRONIZAR COM A NUVEM (STREAMLIT CLOUD)
# =============================================================================
# Ao rodar este script no seu computador (com acesso à VPN/Rede da empresa),
# ele baixa os dados mais recentes do banco EQM e envia automaticamente
# para o GitHub, atualizando o seu dashboard na nuvem sem precisar
# fazer upload manual de planilhas.
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_EXCEL = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.xlsx')
ARQUIVO_CSV   = os.path.join(BASE_DIR, 'Resumo_Atividades_Qualidade_2026.csv')

DB_CONFIG = {
    'database': 'DB_EQM_BI_ENERGIMP',
    'user': 'bi_energimp',
    'password': 'C53BVUYFHCXJD8LUXE5UJYJ8',
    'host': '10.51.1.150',
    'port': 5432
}

def equipe_grupo(cod_equipe):
    cod = str(cod_equipe).upper()
    if 'CE' in cod: return 'CE'
    elif 'BJS' in cod: return 'BJS'
    elif 'AGD' in cod: return 'AGD'
    else: return 'OUTROS'

def atualizar_dados():
    t_inicial = '2026-01-01'
    t_final = datetime.datetime.today().strftime('%Y-%m-%d')

    print("[1/3] Conectando ao banco de dados EQM (10.51.1.150)...")

    # CORREÇÃO: Removemos o LEFT JOIN com bi_osexec_carac (que multiplicava linhas por OS)
    # e com bi_ss (não necessário para o agrupamento). Mantemos apenas os JOINs que
    # fornecem desc_especie, desc_esquema e aerogerador — colunas usadas no groupby.
    # Filtramos diretamente no SQL por desc_numero_os LIKE '%QLW%' para evitar tráfego extra.
    sql = f"""SELECT
        A.cod_os,
        A.cod_equipe,
        A.cod_especie,
        A.cod_esquema,
        F.desc_esquema,
        E.desc_especie,
        right(A.cod_instalacao, 3) || '-' || right(D.desc_localizacao, 2) AS aerogerador,
        A.data_inicio_exec,
        A.data_fim_exec
    FROM "EQM_BI_ENERGIMP".bi_osexec A
    LEFT JOIN "EQM_BI_ENERGIMP".bi_especie E ON E.cod_especie = A.cod_especie
    LEFT JOIN "EQM_BI_ENERGIMP".bi_esquema F ON F.cod_esquema = A.cod_esquema
    LEFT JOIN "EQM_BI_ENERGIMP".bi_ativo   D ON D.cod_ativo   = A.cod_ativo
    WHERE A.data_inicio_exec >= '{t_inicial}'
      AND A.data_inicio_exec <= '{t_final}'
      AND A.os_fechada  = 'Sim'
      AND A.desc_estado = 'EXECUTADA'
      AND A.desc_numero_os LIKE '%QLW%'
    ORDER BY A.data_inicio_exec"""

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(sql)
        resultado = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        df_raw = pd.DataFrame(resultado, columns=colunas) if resultado else pd.DataFrame()
        conn.close()

        if df_raw.empty:
            print("Erro: Nenhum dado encontrado no banco.")
            return False

        print(f"   Banco retornou {len(df_raw)} OS de qualidade (QLW).")
        print("[2/3] Processando e salvando a base...")

        df_raw['grupo_equipe'] = df_raw['cod_equipe'].apply(equipe_grupo)

        # Preencher valores nulos nas colunas de agrupamento ANTES do groupby.
        # Registros com aerogerador/desc_especie/desc_esquema NULL surgem dos LEFT JOINs
        # (ex: ativo sem localização cadastrada, espécie não mapeada).
        # CORREÇÃO PRINCIPAL: dropna=False garante que esses registros NÃO sejam
        # descartados silenciosamente pelo groupby — que é a causa da perda de dados
        # de fevereiro e junho.
        df_raw['aerogerador']  = df_raw['aerogerador'].fillna('N/D')
        df_raw['desc_especie'] = df_raw['desc_especie'].fillna('N/D')
        df_raw['desc_esquema'] = df_raw['desc_esquema'].fillna('N/D')

        tabela = df_raw.groupby(
            ['grupo_equipe', 'data_inicio_exec', 'data_fim_exec',
             'aerogerador', 'desc_especie', 'desc_esquema'],
            dropna=False
        ).size().reset_index(name='quantidade')

        # Salvar Excel (formato principal lido pelo dashboard)
        tabela.to_excel(ARQUIVO_EXCEL, index=False)

        # Salvar CSV com separador ; e encoding UTF-8 BOM (compatível com Excel BR)
        tabela.to_csv(ARQUIVO_CSV, index=False, sep=';', encoding='utf-8-sig')

        print(f"Sucesso: Arquivos atualizados! ({len(tabela)} registros)")

        # Mostrar distribuição por mês para diagnóstico visual
        tabela['data_inicio_exec'] = pd.to_datetime(tabela['data_inicio_exec'])
        por_mes = tabela.groupby(tabela['data_inicio_exec'].dt.month)['quantidade'].sum()
        nomes_mes = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',
                     7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
        print("   Distribuição por mês:")
        for mes, qtd in por_mes.items():
            print(f"     {nomes_mes.get(mes, mes)}: {int(qtd)} atividades")

        return True

    except Exception as e:
        print(f"Erro na extracao: {str(e)}")
        print("Dica: Verifique se voce esta conectado na rede da empresa ou VPN.")
        return False

def sincronizar_github():
    print("[3/3] Sincronizando dados com o GitHub/Nuvem...")
    try:
        # Muda para a raiz do repositório
        os.chdir(BASE_DIR)

        # Adiciona Excel e CSV ao commit
        subprocess.run(["git", "add", "Resumo_Atividades_Qualidade_2026.xlsx"], check=True)
        subprocess.run(["git", "add", "Resumo_Atividades_Qualidade_2026.csv"],  check=True)

        # Adiciona o JSON do PCM caso exista e tenha sido modificado
        if os.path.exists("pcm_atividades_semana.json"):
            subprocess.run(["git", "add", "pcm_atividades_semana.json"], check=False)

        # Tenta comitar (vai retornar código não-zero se não houver mudanças, mas capturamos)
        data_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        r = subprocess.run(
            ["git", "commit", "-m", f"Automated data refresh {data_atual}"],
            capture_output=True
        )

        if b"nothing to commit" in r.stdout or b"nothing to commit" in r.stderr:
            print("Aviso: Nao houve mudancas nos dados desde a ultima atualizacao.")
        else:
            # Faz o push
            print("   Enviando para o repositorio remoto...")
            subprocess.run(["git", "push"], check=True)
            print("Sucesso: Dashboard na nuvem atualizado!")

    except subprocess.CalledProcessError as e:
        print(f"Erro ao sincronizar com o Git: {e}")
        print("Dica: Verifique se o git esta configurado corretamente.")

if __name__ == "__main__":
    print("=" * 60)
    print("INICIANDO ATUALIZACAO PARA A NUVEM")
    print("=" * 60)
    sucesso = atualizar_dados()
    if sucesso:
        sincronizar_github()
    print("=" * 60)
    print("FIM")
    print("=" * 60)
