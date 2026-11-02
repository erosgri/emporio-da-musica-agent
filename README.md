# Agente Empório da Música

Agente conversacional em Python para atendimento da loja fictícia Empório da Música. O
sistema consulta catálogo, estoque, preços, promoções, pedidos e políticas sem permitir que
o modelo acesse diretamente SQL, arquivos ou cadastros de clientes.

## Arquitetura

A solução é híbrida:

- Function calling para produtos, preços, promoções, pagamento e pedidos.
- RAG lexical com BM25 para o manual de políticas.
- SQLite somente leitura durante o atendimento.
- Regras comerciais determinísticas em Python.
- OpenAI para interpretação da intenção e composição da resposta.
- Streamlit como interface de demonstração.

O desenho completo, contratos, Skills e guardrails estão em
[`artefatos_projeto/SDD.md`](artefatos_projeto/SDD.md).

## Requisitos

- Python 3.11 ou superior.
- Chave de API da OpenAI.

## Instalação

### Com `pip`

```bash
python -m pip install -e ".[dev]"
```

### Com `uv`

```bash
uv sync --extra dev
```

Copie o arquivo de ambiente:

```powershell
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
cp .env.example .env
```

Preencha pelo menos:

```dotenv
OPENAI_API_KEY=sua-chave
EMPORIO_MODEL=gpt-4.1-mini
```

O modelo e a URL base são configuráveis. O provedor alternativo precisa oferecer contratos
compatíveis com function calling e saída JSON estruturada.

## Execução

### Interface web

```bash
python -m streamlit run app.py
```

### Terminal

```bash
emporio-cli
```

Na primeira execução, os CSVs são validados e importados para
`data/processed/emporio.db`. O PDF também é extraído e indexado em
`data/processed/policy_chunks.json`. Os dois artefatos são reconstruídos quando necessário.

## Ferramentas do agente

- `search_products`: busca instrumentos por texto, categoria, preço e especificações.
- `get_product`: consulta detalhes, estoque e promoção de um instrumento.
- `calculate_purchase_options`: calcula promoção, PIX e parcelamento.
- `get_order_status`: consulta um pedido após validação de identidade.
- `search_store_policy`: recupera trechos citáveis do manual.
- `get_store_information`: retorna endereço, horário e contatos normalizados.

Não existe ferramenta genérica de SQL, leitura de arquivos ou execução de código.

## Regras relevantes

- Produto disponível exige status `active` e estoque maior que zero.
- Somente promoções com `is_active = true` são aplicadas.
- Promoção e desconto de 5% no PIX não são cumulativos.
- Totais históricos de pedidos não são recalculados.
- Pedido exige número e e-mail completo ou telefone associado.
- Políticas devem ser acompanhadas de seção e página.
- Sem evidência suficiente, o agente pede esclarecimento ou encaminha para atendimento.

## Testes e qualidade

```bash
python -m pytest --cov=emporio_agent --cov-report=term-missing
python -m ruff check .
python -m mypy src
```

Os testes cobrem ingestão, disponibilidade, promoções, PIX, parcelamento, pedidos,
recuperação das políticas, contratos das ferramentas e guardrails de fundamentação.

## Estrutura

```text
.
├── app.py
├── artefatos_projeto/
│   ├── SDD.md
│   ├── políticas_da_loja.pdf
│   └── *.csv
├── examples/
├── src/emporio_agent/
├── tests/
└── data/processed/
```

## Decisões e suposições

- O campo `is_active` é a fonte de verdade para promoções, pois não existem datas de
  vigência nos dados.
- Regras detalhadas de parcelamento prevalecem sobre a descrição geral do manual.
- O número `(67) 3341-4444` é tratado como telefone geral e `(67) 3321-4500` como
  WhatsApp.
- Divergências de nome, descrição e especificações dos produtos não são corrigidas
  silenciosamente.
- Informações “em tempo real” significam consultar a cópia local dos dados fornecidos.

## Limitações

- Não há integração real com WhatsApp, estoque, pagamento ou transportadoras.
- A validação de pedidos é adequada ao protótipo, não substitui autenticação de produção.
- O RAG inicial é lexical; perguntas muito indiretas podem exigir expansão adicional.
- O histórico existe somente durante a sessão.
- O agente não efetua compras, cancelamentos, devoluções ou abertura de chamados.
- A execução com LLM depende de uma chave e da disponibilidade do provedor.

## Próximas evoluções

- API FastAPI e integração com canais reais.
- Autenticação forte para pedidos.
- PostgreSQL e sincronização com sistemas operacionais.
- Busca híbrida lexical e vetorial, caso as avaliações mostrem ganho.
- Avaliação conversacional automatizada e observabilidade centralizada.
- Transferência do contexto para atendimento humano.

## Uso de assistente de código

O Cursor foi utilizado para analisar o enunciado e os dados, estruturar o SDD, implementar
o protótipo, criar testes e revisar a documentação. As decisões de arquitetura foram
registradas explicitamente, e regras críticas foram mantidas em código determinístico para
que o comportamento não dependa apenas das sugestões do modelo.
