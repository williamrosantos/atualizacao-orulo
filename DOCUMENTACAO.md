# Documentação — Integração API Órulo → Power BI
**Projeto:** Análise da Concorrência | Prestes
**Última atualização:** 08/04/2026

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
| `orulo_extracao.py` | Script de produção — autentica, extrai lista + detalhes e salva CSV |
| `orulo_teste.py` | Script de diagnóstico — testa autenticação e qualidade dos dados |
| `.github/workflows/extracao_diaria.yml` | Workflow que agenda e executa o script diariamente |
| `requirements.txt` | Dependências Python instaladas no GitHub Actions |
| `data/orulo_empreendimentos.csv` | Arquivo de saída lido pelo Power BI |
| `.env` | Credenciais locais (não vai ao GitHub — está no .gitignore) |

---

## Credenciais da API Órulo

As credenciais **não estão no código**. Estão armazenadas em dois lugares:

**No GitHub Actions (produção):** GitHub Secrets
`Repositório → Settings → Secrets and variables → Actions`

| Secret | Descrição |
|---|---|
| `ORULO_CLIENT_ID` | Client ID da aplicação Órulo |
| `ORULO_CLIENT_SECRET` | Client Secret da aplicação Órulo |

**Localmente:** arquivo `.env` na raiz do projeto
```
ORULO_CLIENT_ID=sua_chave
ORULO_CLIENT_SECRET=seu_secret
```

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
- **Notificação de falha:** GitHub envia e-mail automático ao dono do repositório

---

## Praças extraídas

| Cidade | Estado | Status |
|---|---|---|
| Ponta Grossa | PR | ativo |
| Curitiba | PR | ativo |
| Guarapuava | PR | sem dados na Órulo (mantido para monitorar) |
| Londrina | PR | ativo |
| Maringá | PR | sem dados na Órulo (mantido para monitorar) |

Para adicionar ou remover cidades, edite a variável `PRAÇAS` em `orulo_extracao.py`.

---

## Como funciona a extração

O script faz **duas chamadas por empreendimento**:

1. **Endpoint de listagem** (`/buildings`) — paginado, retorna dados básicos
2. **Endpoint de detalhe** (`/buildings/{id}`) — retorna `data_lancamento`, `data_entrega` e `total_unidades` que não existem na listagem

Um delay de **0.3s** entre cada chamada de detalhe evita bloqueio por rate limiting da API.

---

## Arquivo CSV gerado

- **Caminho no repositório:** `data/orulo_empreendimentos.csv`
- **URL para o Power BI:**
  ```
  https://raw.githubusercontent.com/williamrosantos/atualizacao-orulo/main/data/orulo_empreendimentos.csv
  ```
- O arquivo é **sempre substituído** a cada extração — mesmo link, dados atualizados.

### Campos do CSV (28 colunas)

| Campo | Fonte | Descrição |
|---|---|---|
| `id` | listagem | ID do empreendimento na Órulo |
| `nome` | listagem | Nome do empreendimento |
| `cidade` | listagem | Cidade |
| `estado` | listagem | Estado |
| `bairro` | listagem | Bairro |
| `status` | listagem | Status (Em construção, Pronto, etc.) |
| `fase` | listagem | Fase (Lançamento, Em obras, etc.) |
| `data_lancamento` | **detalhe** | Data de lançamento |
| `data_entrega` | **detalhe** | Data prevista de entrega |
| `total_unidades` | **detalhe** | Total de unidades do empreendimento |
| `preco_minimo` | listagem | Preço mínimo (R$) |
| `preco_m2_privativo` | listagem | Preço por m² privativo |
| `area_minima_m2` | listagem | Área mínima (m²) |
| `area_maxima_m2` | listagem | Área máxima (m²) |
| `quartos_min` | listagem | Quartos mínimo |
| `quartos_max` | listagem | Quartos máximo |
| `suites_min` | listagem | Suítes mínimo |
| `suites_max` | listagem | Suítes máximo |
| `vagas_min` | listagem | Vagas mínimo |
| `vagas_max` | listagem | Vagas máximo |
| `andares` | listagem | Número de andares |
| `aptos_por_andar` | listagem | Apartamentos por andar |
| `estoque` | listagem | Unidades disponíveis em estoque |
| `finalidade` | listagem | Finalidade (Residencial, Comercial) |
| `construtora` | listagem | Nome da construtora |
| `portfolio` | listagem | Portfolio (Lançamento, etc.) |
| `atualizado_em` | listagem | Última atualização na Órulo |
| `data_extracao` | script | Data em que o dado foi extraído |

---

## Conexão com Power BI

### Power BI Desktop
1. **Obter Dados → Web**
2. Cole a URL do CSV
3. Clique em OK → Carregar

### Atualização do schema (quando o CSV mudar de estrutura)
1. **Transformar dados** (Power Query Editor)
2. No painel **"Etapas Aplicadas"**, apague todas as etapas exceto `Fonte`
3. **Fechar e Aplicar**

### Power BI Service (atualização automática)
1. Publique o relatório no Power BI Service
2. **Conjunto de dados → Agendar atualização**
3. Configure o horário (recomendado: após 07h BRT)
4. Não é necessário gateway — o arquivo está em URL pública

---

## Como rodar localmente

```powershell
# Instalar dependências
pip install -r requirements.txt

# Rodar extração (credenciais lidas do .env automaticamente)
python orulo_extracao.py

# Rodar diagnóstico
python orulo_teste.py
```

---

## Monitoramento

- **Ver execuções:** GitHub → Actions → Extração Diária Órulo
- Cada execução mostra quantos empreendimentos foram coletados por cidade, quantos detalhes falharam e o tempo total

---

## Manutenção

| Situação | O que fazer |
|---|---|
| Credencial da API expirou | Atualizar os GitHub Secrets e o `.env` local |
| Adicionar nova cidade | Editar `PRAÇAS` em `orulo_extracao.py` e fazer push |
| Mudar horário da extração | Editar `cron` em `.github/workflows/extracao_diaria.yml` |
| Extração falhou | GitHub → Actions → ver log do erro |
| PBI não mostra novas colunas | Power Query → apagar etapas exceto `Fonte` → Fechar e Aplicar |
| Muitos detalhes falhando | Aumentar o delay em `time.sleep(0.3)` no script |
