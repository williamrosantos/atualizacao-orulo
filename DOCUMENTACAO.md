# Documentação — Integração API Órulo → Power BI
**Projeto:** Análise da Concorrência | Prestes  
**Data:** 08/04/2026  

---

## Visão Geral

Extração diária automática de empreendimentos da API Órulo, publicação no GitHub e conexão com Power BI.

```
API Órulo → GitHub Actions (diário 06h) → CSV no GitHub → Power BI
```

---

## Arquitetura

| Componente | Descrição |
|---|---|
| `orulo_extracao.py` | Script Python que autentica na API e extrai os dados |
| `.github/workflows/extracao_diaria.yml` | Workflow que agenda e executa o script diariamente |
| `data/orulo_empreendimentos.csv` | Arquivo de saída lido pelo Power BI |

---

## Credenciais da API Órulo

As credenciais **não estão no código**. Estão armazenadas como GitHub Secrets:

| Secret | Descrição |
|---|---|
| `ORULO_CLIENT_ID` | Client ID da aplicação Órulo |
| `ORULO_CLIENT_SECRET` | Client Secret da aplicação Órulo |

Para visualizar ou atualizar:  
`GitHub → Repositório → Settings → Secrets and variables → Actions`

---

## Repositório GitHub

- **URL:** https://github.com/williamrosantos/atualizacao-orulo
- **Visibilidade:** Público (necessário para o Power BI acessar o CSV sem autenticação)
- **Branch principal:** `main`

---

## Agendamento (GitHub Actions)

- **Horário:** Todo dia às **06:00 BRT** (09:00 UTC)
- **Arquivo de configuração:** `.github/workflows/extracao_diaria.yml`
- **Para rodar manualmente:** GitHub → Actions → Extração Diária Órulo → Run workflow

---

## Praças extraídas

| Cidade | Estado |
|---|---|
| Ponta Grossa | PR |
| Curitiba | PR |
| Guarapuava | PR |
| Londrina | PR |
| Maringá | PR |

Para adicionar ou remover cidades, edite a variável `PRAÇAS` em `orulo_extracao.py`.

---

## Arquivo CSV gerado

- **Caminho no repositório:** `data/orulo_empreendimentos.csv`
- **URL para o Power BI:**
  ```
  https://raw.githubusercontent.com/williamrosantos/atualizacao-orulo/main/data/orulo_empreendimentos.csv
  ```
- O arquivo é **sempre substituído** a cada extração — mesmo link, dados atualizados.

### Campos do CSV

| Campo | Descrição |
|---|---|
| `id` | ID do empreendimento na Órulo |
| `nome` | Nome do empreendimento |
| `cidade` | Cidade |
| `estado` | Estado |
| `bairro` | Bairro |
| `status` | Status (disponível, vendido, etc.) |
| `data_lancamento` | Data de lançamento |
| `data_entrega` | Data de entrega |
| `preco_minimo` | Preço mínimo (R$) |
| `preco_m2_privativo` | Preço por m² privativo |
| `area_minima_m2` | Área mínima (m²) |
| `area_maxima_m2` | Área máxima (m²) |
| `quartos_min` | Quartos mínimo |
| `quartos_max` | Quartos máximo |
| `total_unidades` | Total de unidades |
| `estoque` | Unidades em estoque |
| `finalidade` | Finalidade (residencial, comercial) |
| `portfolio` | Portfolio da construtora |
| `data_extracao` | Data em que o dado foi extraído |

---

## Conexão com Power BI

### Power BI Desktop
1. **Obter Dados → Web**
2. Cole a URL do CSV
3. Clique em OK → Carregar
4. Para atualizar: clique em **"Atualizar"** na faixa de opções

### Power BI Service (atualização automática)
1. Publique o relatório no Power BI Service
2. Vá em **Conjunto de dados → Agendar atualização**
3. Configure o horário desejado (recomendado: após 07h, para garantir que a extração já terminou)
4. Não é necessário gateway — o arquivo está em URL pública

---

## Como rodar localmente (opcional)

```bash
# Instalar dependências
pip install requests pandas openpyxl

# Rodar extração
python orulo_extracao.py
```

O CSV será salvo em `data/orulo_empreendimentos.csv` localmente.

---

## Monitoramento

- **Ver execuções:** GitHub → Actions → Extração Diária Órulo
- **Log local:** `extracao.log` (gerado ao rodar localmente)
- Cada execução mostra quantos empreendimentos foram coletados por cidade e o tempo total

---

## Manutenção

| Situação | O que fazer |
|---|---|
| Credencial da API expirou | Atualizar os GitHub Secrets |
| Adicionar nova cidade | Editar `PRAÇAS` em `orulo_extracao.py` e fazer push |
| Mudar horário da extração | Editar `cron` em `.github/workflows/extracao_diaria.yml` |
| Extração falhou | GitHub → Actions → ver log do erro |
