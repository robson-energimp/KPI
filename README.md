# ⚡ KPI Qualidade - Energimp

Dashboard interativo para acompanhamento semanal das atividades da equipe de Qualidade em aerogeradores.

## 📊 Funcionalidades

- **Painel Principal**: KPIs, gráficos de evolução semanal e detalhamento por regional
- **Planejamento PCM**: Gestão de atividades planejadas pela equipe de PCM
- **Geração de Relatórios**: Exportação em PDF corporativo e Excel

## 🚀 Como Usar

### Streamlit Cloud (Online)
Acesse diretamente pelo link do Streamlit Cloud. Use o **Upload de Excel** na sidebar para carregar os dados.

### Localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Estrutura

| Arquivo | Descrição |
|---------|-----------|
| `app.py` | Interface Streamlit principal |
| `backend.py` | Módulo de dados (EQM + Excel) |
| `relatorio_pdf_corporativo.py` | Gerador de relatório PDF |
| `requirements.txt` | Dependências Python |

## 📝 Atualização de Dados

1. Rodar localmente e clicar em **Atualizar Dados do EQM**
2. O Excel `Resumo_Atividades_Qualidade_2026.xlsx` será atualizado automaticamente
3. Fazer commit e push para o GitHub
4. O Streamlit Cloud recarrega automaticamente

---
*Energimp - Equipe de Qualidade*
