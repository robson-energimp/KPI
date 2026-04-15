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
    WHERE A.data_inicio_exec >= '{t_inicial}' AND A.data_inicio_exec <= '{t_final}'
    AND A.os_fechada = 'Sim' AND A.desc_estado = 'EXECUTADA'
    ORDER BY A.data_criacao"""

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
            
        print("[2/3] Processando e salvando a base Excel...")
        os_qlw = df_raw[df_raw['desc_numero_os'].str.contains('QLW', na=False)].copy()
        os_qlw['grupo_equipe'] = os_qlw['cod_equipe'].apply(equipe_grupo)

        tabela = os_qlw.groupby(
            ['grupo_equipe', 'data_inicio_exec', 'data_fim_exec', 'aerogerador', 'desc_especie', 'desc_esquema']
        ).size().reset_index(name='quantidade')
        
        tabela.to_excel(ARQUIVO_EXCEL, index=False)
        print(f"Sucesso: Excel atualizado! ({len(tabela)} registros)")
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
        
        # Faz commit do novo Excel ou JSON (caso haja PCM novo também)
        subprocess.run(["git", "add", "Resumo_Atividades_Qualidade_2026.xlsx"], check=True)
        
        # Adiciona o JSON do PCM caso exista e tenha sido modificado
        if os.path.exists("pcm_atividades_semana.json"):
            subprocess.run(["git", "add", "pcm_atividades_semana.json"], check=False)
            
        # Tenta comitar (vai falhar e continuar se não houver mudanças)
        data_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        r = subprocess.run(["git", "commit", "-m", f"Automated data refresh {data_atual}"], capture_output=True)
        
        if b"nothing to commit" in r.stdout:
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
