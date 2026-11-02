# Software Design Document — Agente Empório da Música

**Versão:** 0.1  
**Status:** Rascunho para revisão  
**Linguagem principal:** Python  
**Última atualização:** 02/11/2026

## 1. Visão geral

Este documento descreve o projeto de um agente conversacional para auxiliar o atendimento da loja fictícia Empório da Música.

O agente deverá responder dúvidas sobre produtos e políticas, consultar pedidos, apresentar preços e promoções válidas e recomendar instrumentos disponíveis. As respostas deverão ser baseadas exclusivamente nos dados fornecidos ou em regras explicitamente documentadas.

## 2. Objetivos

### 2.1 Objetivos funcionais

- Atender clientes por mensagens de texto em português brasileiro.
- Consultar catálogo, preços, estoque e especificações.
- Consultar promoções ativas e calcular preços promocionais.
- Consultar status, entrega e rastreamento de pedidos.
- Responder perguntas sobre horários, endereço, pagamentos, entregas, trocas, devoluções e garantias.
- Recomendar alternativas quando um produto estiver indisponível ou descontinuado.
- Manter o contexto durante uma conversa.
- Encaminhar situações que exijam atendimento humano.

### 2.2 Objetivos de qualidade

- Evitar respostas inventadas.
- Preservar dados pessoais dos clientes.
- Tornar as regras comerciais determinísticas e testáveis.
- Manter baixo acoplamento entre o modelo de linguagem e as fontes de dados.
- Permitir a troca do provedor de LLM com impacto reduzido.
- Ser simples de executar e avaliar localmente.

## 3. Fora do escopo

- Efetuar compras, pagamentos, cancelamentos ou alterações reais.
- Integrar-se a WhatsApp, Correios, Jadlog ou sistemas externos reais.
- Atualizar produtos, pedidos, clientes ou promoções.
- Vender acessórios, amplificadores, pedais, cabos, cases, palhetas ou cordas.
- Substituir um atendente humano em reclamações ou exceções não previstas.
- Fornecer aconselhamento jurídico sobre o Código de Defesa do Consumidor.

## 4. Usuários e casos de uso

### 4.1 Cliente

- Procurar instrumentos por categoria, orçamento ou característica.
- Verificar preço, promoção e disponibilidade.
- Solicitar recomendação entre produtos.
- Consultar um pedido próprio.
- Entender políticas e condições comerciais.

### 4.2 Avaliador técnico

- Executar o projeto localmente.
- Testar cenários pelo chat.
- Compreender as decisões técnicas pelo README e por este documento.
- Executar testes automatizados.

## 5. Requisitos funcionais

| ID | Requisito |
|---|---|
| RF-01 | O agente deve responder em português brasileiro com tom informal e profissional. |
| RF-02 | Toda informação de preço, estoque ou status deve ser obtida por ferramenta. |
| RF-03 | O agente deve filtrar produtos por nome, categoria, preço, estoque e especificações. |
| RF-04 | Um produto somente deve ser anunciado como disponível quando estiver ativo e possuir estoque maior que zero. |
| RF-05 | Promoções somente devem ser aplicadas quando `is_active` for verdadeiro. |
| RF-06 | O desconto de PIX não deve ser acumulado com preço promocional. |
| RF-07 | O agente deve informar preço original, percentual de desconto e preço promocional. |
| RF-08 | A consulta de pedido deve validar a identidade do cliente antes de revelar dados. |
| RF-09 | O agente não deve revelar dados pessoais na resposta, exceto os estritamente necessários ao atendimento. |
| RF-10 | Políticas devem ser recuperadas do manual fornecido. |
| RF-11 | Produtos indisponíveis devem gerar sugestões equivalentes disponíveis, quando existirem. |
| RF-12 | Perguntas fora do escopo devem ser recusadas educadamente. |
| RF-13 | Casos ambíguos, reclamações e exceções devem ser encaminhados ao atendimento humano. |
| RF-14 | O agente deve preservar o contexto da sessão atual. |

## 6. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Segredos devem ser fornecidos por variáveis de ambiente. |
| RNF-02 | O projeto deve executar em Python 3.11 ou superior. |
| RNF-03 | As ferramentas devem possuir contratos tipados e validação de entrada. |
| RNF-04 | As regras comerciais críticas devem possuir testes unitários. |
| RNF-05 | Falhas do LLM ou das ferramentas devem produzir uma resposta segura, sem dados fabricados. |
| RNF-06 | Logs não devem registrar telefone, e-mail ou outros dados pessoais completos. |
| RNF-07 | O provedor e o modelo devem ser configuráveis. |
| RNF-08 | O projeto deve funcionar em Windows, Linux e macOS. |

## 7. Decisões de arquitetura

### 7.1 Abordagem

Será adotada uma arquitetura híbrida:

1. **Function calling** para dados estruturados e regras determinísticas.
2. **Retrieval** para localizar trechos relevantes do manual de políticas.
3. **LLM** para interpretar a intenção, selecionar ferramentas e redigir a resposta.

RAG puro não é adequado para preços, estoque ou pedidos, pois buscas semânticas não garantem resultados exatos. Um agente SQL genérico também não será exposto ao modelo, reduzindo consultas imprevisíveis e risco de acesso indevido.

### 7.2 Fluxo principal

```text
Mensagem do cliente
        |
        v
Orquestrador do agente
        |
        +--> Ferramentas de catálogo e promoções --> SQLite
        |
        +--> Ferramenta de pedidos -------------> SQLite
        |
        +--> Ferramenta de políticas -----------> Índice de documentos
        |
        v
Validação da resposta
        |
        v
Resposta ao cliente
```

### 7.3 Interface

A interface inicial será um chat em Streamlit. Uma CLI poderá ser mantida como alternativa simples para testes e automação.

### 7.4 Persistência

- Os CSVs serão importados para um banco SQLite local.
- O histórico será mantido durante a sessão do chat.
- Não haverá persistência permanente de conversas na primeira versão.
- O banco será somente leitura durante o atendimento.

### 7.5 Stack técnica

| Área | Ferramenta | Justificativa |
|---|---|---|
| Linguagem | Python 3.12 | Ecossistema adequado para LLMs, dados e prototipação. |
| Dependências | `uv` e `pyproject.toml` | Instalação rápida e ambiente reproduzível. |
| LLM | OpenAI `gpt-4.1-mini` | Bom equilíbrio entre custo, latência e suporte a function calling. |
| Integração com LLM | SDK oficial `openai` | Menor complexidade e controle explícito do ciclo de ferramentas. |
| Configuração | `pydantic-settings` | Validação tipada das variáveis de ambiente. |
| Contratos | `pydantic` | Entradas e saídas tipadas para ferramentas e domínio. |
| Banco local | `sqlite3` | Nativo do Python, suficiente para o volume fornecido. |
| Leitura dos CSVs | Biblioteca padrão `csv` | Evita dependência pesada para uma ingestão pequena. |
| Leitura do PDF | `pypdf` | Extração suficiente para o manual textual fornecido. |
| Busca de políticas | `rank-bm25` | Busca lexical leve, local e explicável para um documento pequeno. |
| Interface | `streamlit` | Chat demonstrável com baixo custo de implementação. |
| Testes | `pytest` e `pytest-cov` | Testes unitários, integração e cobertura. |
| Qualidade | `ruff` | Formatação e lint em uma única ferramenta rápida. |
| Tipagem | `mypy` | Verificação estática das principais camadas. |
| Automação | GitHub Actions | Execução de lint e testes a cada push ou pull request. |
| Logs | `logging` da biblioteca padrão | Observabilidade sem nova dependência. |

O nome do modelo, a chave e a URL base serão configuráveis por ambiente. O modelo acima será o padrão de referência, sem impedir o uso de outro modelo compatível com tool calling.

## 8. Componentes

### 8.1 Interface de chat

Responsabilidades:

- Receber mensagens.
- Exibir histórico e respostas.
- Gerenciar identificador da sessão.
- Exibir erros recuperáveis sem detalhes internos.

### 8.2 Orquestrador

Responsabilidades:

- Aplicar o prompt de sistema.
- Enviar o histórico relevante ao LLM.
- Executar chamadas de ferramentas.
- Limitar o número de ciclos de ferramentas.
- Produzir fallback seguro em caso de falha.

### 8.3 Camada de ferramentas

Somente as ferramentas abaixo serão expostas ao LLM. Consultas auxiliares e regras de negócio permanecerão internas.

#### `search_products`

Busca instrumentos usando filtros combináveis.

Entradas:

- `query`: nome, marca ou descrição.
- `category`: nome da categoria.
- `min_price` e `max_price`: faixa de preço.
- `strings`: nylon ou aço, quando aplicável.
- `electronics`: presença de captação, quando aplicável.
- `available_only`: por padrão, verdadeiro.
- `limit`: máximo de resultados, limitado pelo sistema.

Saída:

- Lista resumida com ID, nome, preço, status, estoque e eventual promoção ativa.

#### `get_product`

Retorna os dados atuais de um instrumento por ID ou nome aproximado.

Entradas:

- `product_id` ou `product_name`.

Saída:

- Dados do produto, especificações, disponibilidade, preço original e promoção ativa.

#### `calculate_purchase_options`

Calcula opções de pagamento para um produto sem efetuar uma compra.

Entradas:

- `product_id`.

Saída:

- Preço de tabela.
- Preço promocional, quando aplicável.
- Preço no PIX, respeitando a não cumulatividade.
- Quantidade máxima de parcelas permitida.
- Valor de cada parcela.

#### `get_order_status`

Consulta um pedido após validar a identidade do cliente.

Entradas:

- `order_id`.
- `customer_identifier`: e-mail completo ou telefone associado.

Saída:

- Status, data, total, itens, rastreamento e previsão, quando disponíveis.
- Nenhum dado cadastral do cliente.

#### `search_store_policy`

Recupera trechos relevantes e citáveis do manual.

Entradas:

- `topic`: pergunta ou assunto pesquisado.
- `limit`: máximo de trechos, limitado pelo sistema.

Saída:

- Seção, título, página, conteúdo e pontuação de relevância.

#### `get_store_information`

Retorna informações gerais normalizadas da loja.

Entradas:

- `field`: endereço, horário, telefone, WhatsApp, e-mail ou escopo do catálogo.

Saída:

- Informação solicitada e referência da seção do manual.

### 8.3.1 Funções não expostas ao LLM

As funções abaixo serão internas:

- Importação e validação dos CSVs.
- Listagem ou busca de clientes.
- Cálculo do preço promocional.
- Normalização de telefone e e-mail.
- Execução de SQL.
- Ranqueamento das políticas.
- Mascaramento de dados pessoais.
- Geração de alternativas para produto indisponível, reutilizando os filtros do catálogo.

Não será criada uma ferramenta genérica de SQL, leitura de arquivos ou execução de código.

### 8.4 Skills do agente

Uma Skill representa uma capacidade de negócio do agente. Ela define intenção, ferramentas permitidas, pré-condições, regras e resultado esperado. Skills não executam SQL nem acessam arquivos diretamente.

#### Skill 1 — Descoberta de instrumentos

**Intenções:** procurar, filtrar ou recomendar instrumentos.

**Ferramentas permitidas:** `search_products` e `get_product`.

**Contrato:**

- Aceitar filtros explícitos e inferidos da conversa.
- Pedir esclarecimento quando categoria, orçamento ou característica forem indispensáveis.
- Retornar somente produtos compatíveis com os filtros.
- Considerar disponível apenas produto `active` com estoque maior que zero.
- Limitar a resposta às opções mais relevantes, sem despejar todo o catálogo.

**Fallback:** quando não houver resultado, explicar quais filtros não foram atendidos e oferecer ampliar preço ou características.

#### Skill 2 — Detalhes e comparação de instrumentos

**Intenções:** consultar um modelo ou comparar opções.

**Ferramentas permitidas:** `get_product` e, para vários itens, `search_products`.

**Contrato:**

- Resolver ambiguidades de nome antes de afirmar dados.
- Comparar somente campos presentes nos contratos dos produtos.
- Não inferir qualidade, material ou adequação que não esteja nos dados.
- Mostrar indisponibilidade ou descontinuação com transparência.

**Fallback:** solicitar marca ou modelo quando houver múltiplas correspondências.

#### Skill 3 — Preço, promoção e pagamento

**Intenções:** consultar preço final, PIX, promoção ou parcelamento.

**Ferramentas permitidas:** `get_product` e `calculate_purchase_options`.

**Contrato:**

- Nunca calcular valores livremente no texto do LLM.
- Usar valores monetários calculados pela camada de domínio com `Decimal`.
- Aplicar somente promoções ativas.
- Nunca acumular promoção com desconto de PIX.
- Exibir preço original, desconto e preço final quando houver promoção.

**Fallback:** se o produto não for identificado, solicitar o modelo antes de calcular.

#### Skill 4 — Acompanhamento de pedido

**Intenções:** consultar status, itens, entrega ou rastreamento.

**Ferramenta permitida:** `get_order_status`.

**Contrato:**

- Exigir número do pedido e e-mail completo ou telefone.
- Não confirmar se um pedido existe antes da validação.
- Não revelar nome, telefone, e-mail, cidade ou outros dados cadastrais.
- Não inventar previsão ou código de rastreamento ausente.
- Não permitir consulta de pedidos por nome de cliente.

**Fallback:** em falha de validação, responder de forma neutra e solicitar revisão dos dados.

#### Skill 5 — Orientação sobre políticas

**Intenções:** dúvidas sobre pagamento, troca, devolução, garantia, frete, privacidade e atendimento.

**Ferramentas permitidas:** `search_store_policy` e, quando necessário, `get_store_information`.

**Contrato:**

- Fundamentar a resposta nos trechos recuperados.
- Informar seção e página da política.
- Fazer perguntas adicionais quando a regra depender de canal, data, defeito ou estado do produto.
- Não converter orientação operacional em aconselhamento jurídico.
- Encaminhar casos não cobertos ou conflitantes ao atendimento humano.

**Fallback:** declarar que a política não foi localizada; nunca completar a lacuna com conhecimento geral do modelo.

#### Skill 6 — Informações da loja

**Intenções:** endereço, horário, contato e escopo do catálogo.

**Ferramenta permitida:** `get_store_information`.

**Contrato:**

- Retornar somente o campo solicitado.
- Diferenciar telefone geral de WhatsApp.
- Informar horário especial apenas quando houver dado explícito.
- Explicar que a loja vende instrumentos, não acessórios.

#### Skill 7 — Limite de escopo e encaminhamento

**Intenções:** assuntos sem relação com a loja, reclamações, exceções ou solicitações de ação real.

**Ferramentas permitidas:** `get_store_information`, apenas quando for necessário fornecer o canal de contato.

**Contrato:**

- Recusar assuntos externos de forma breve e cordial.
- Não simular compra, cancelamento, reembolso ou abertura real de chamado.
- Em reclamações, demonstrar empatia e indicar o canal humano.
- Não prometer prazo diferente das 24 horas úteis previstas na política.

#### Skill 8 — Continuidade da conversa

**Intenções:** perguntas subsequentes que dependem de produto, pedido ou política mencionados anteriormente.

**Ferramentas permitidas:** as ferramentas da Skill de negócio ativa.

**Contrato:**

- Reutilizar apenas contexto inequívoco da sessão.
- Solicitar confirmação quando existirem vários produtos ou pedidos possíveis.
- Não manter dados pessoais após o encerramento da sessão.
- Não tratar respostas anteriores do modelo como fonte de verdade; dados dinâmicos devem ser consultados novamente.

### 8.5 Repositórios de dados

Responsabilidades:

- Encapsular consultas SQL.
- Retornar modelos tipados.
- Impedir SQL produzido pelo LLM.
- Centralizar filtros de disponibilidade e privacidade.

### 8.6 Ingestão

Responsabilidades:

- Validar cabeçalhos e tipos dos CSVs.
- Validar integridade referencial.
- Normalizar valores booleanos, datas e JSON de especificações.
- Importar os dados para SQLite.
- Extrair e dividir o manual em seções.
- Produzir relatório de inconsistências sem alterar silenciosamente a fonte.

## 9. Modelo de dados

### 9.1 Entidades principais

- `Category`
- `Product`
- `Promotion`
- `Customer`
- `Order`
- `OrderItem`
- `PolicySection`

### 9.2 Relacionamentos

```text
Category 1 ---- N Product
Product  1 ---- N Promotion
Customer 1 ---- N Order
Order    1 ---- N OrderItem
Product  1 ---- N OrderItem
```

### 9.3 Regra de disponibilidade

Um produto está disponível para venda quando:

```text
product.status = "active" AND product.stock_quantity > 0
```

Produtos `coming_soon`, `discontinued` ou com estoque zero não devem ser oferecidos como disponíveis.

## 10. Regras comerciais

### 10.1 Promoções

- Somente registros com `is_active = true` são válidos.
- O preço promocional deve ser calculado com arredondamento monetário em duas casas decimais.
- O desconto de 5% no PIX não é cumulativo com promoções.
- Em uma promoção, a resposta deve apresentar preço original, desconto e preço final.
- Na ausência de datas de vigência, `is_active` será considerado a fonte de verdade.

### 10.2 Parcelamento

- Até 3 parcelas: sem juros; compras inferiores a R$ 50,00 não serão parceladas.
- De 4 a 6 parcelas: parcela mínima de R$ 80,00.
- De 7 a 12 parcelas: parcela mínima de R$ 100,00.
- Combinação PIX e cartão somente para compras acima de R$ 2.000,00.
- As regras detalhadas de parcelamento terão precedência sobre a descrição geral do manual.

### 10.3 Trocas, devoluções e garantia

- Arrependimento de compra online: até 7 dias corridos após o recebimento.
- Troca por preferência: até 7 dias, condicionada ao estado e à disponibilidade.
- Troca direta por defeito: até 30 dias após a compra.
- Garantia legal: 90 dias contra defeitos de fabricação.
- Casos sem informações suficientes devem ser encaminhados a um atendente.

### 10.4 Pedidos

- Totais históricos não serão recalculados com preços ou promoções atuais.
- Rastreamento somente será apresentado para pedidos que possuam código.
- Pedidos sem rastreamento devem ser explicados conforme seu status, sem estimativas inventadas.

## 11. Privacidade e segurança

### 11.1 Validação de pedido

Antes de revelar um pedido, o cliente deverá informar:

- Número do pedido; e
- E-mail completo ou telefone associado ao cadastro.

Os valores serão comparados de forma normalizada. A resposta não exibirá os dados fornecidos nem outros dados cadastrais.

### 11.2 Proteções

- Não permitir consultas de listagem de clientes.
- Não disponibilizar ferramenta de busca de cliente ao LLM.
- Não incluir registros completos no prompt.
- Mascarar dados pessoais nos logs.
- Limitar tamanho de mensagens e quantidade de chamadas por turno.
- Tratar o conteúdo recuperado como dados, nunca como instruções de sistema.

## 12. Estratégia de prompt

### 12.1 Prompt de sistema

O prompt de sistema deverá:

- Definir a persona como especialista acolhedor em instrumentos musicais.
- Exigir consulta às ferramentas para preços, estoque, promoções e pedidos.
- Proibir suposições e informações inventadas.
- Orientar respostas curtas e objetivas.
- Diferenciar informação confirmada de limitação.
- Recusar solicitações fora do escopo.
- Encaminhar reclamações e exceções a atendimento humano.
- Impedir exposição de dados pessoais.

As regras comerciais críticas permanecerão no código. O prompt orientará o comportamento, mas não será a única barreira de segurança.

### 12.2 Princípio dos guardrails

Os guardrails seguirão o princípio de **falhar de forma fechada**: quando não houver evidência suficiente, a resposta deverá declarar a limitação, pedir esclarecimento ou encaminhar ao atendimento humano. Fluência do texto não será considerada evidência de correção.

As proteções serão implementadas em código, contratos e validações. Instruções no prompt serão uma camada complementar, não o único controle.

### 12.3 Guardrails de entrada

- Limitar cada mensagem a 2.000 caracteres.
- Rejeitar conteúdo vazio ou formado apenas por espaços.
- Tratar toda mensagem como entrada não confiável.
- Não executar URLs, código, SQL, comandos ou conteúdo anexado pelo usuário.
- Ignorar pedidos para revelar o prompt, alterar regras, desabilitar segurança ou simular ferramentas.
- Não permitir que o usuário escolha nomes de ferramentas ou argumentos internos diretamente.
- Normalizar Unicode para reduzir variações maliciosas sem modificar o texto original registrado.
- Mascarar telefone e e-mail antes de registrar logs.

Sinais de prompt injection serão usados para restringir o fluxo, mas não serão considerados um detector infalível. A segurança não dependerá apenas de classificar a mensagem como maliciosa.

### 12.4 Guardrails de roteamento

- Cada turno deverá ser associado a uma das Skills definidas na seção 8.4.
- Cada Skill terá uma lista fechada de ferramentas permitidas.
- Uma chamada fora da lista permitida será bloqueada pelo orquestrador.
- Preço, estoque, promoção, pedido, rastreamento, contato e horário sempre exigirão ferramenta.
- Políticas sempre exigirão `search_store_policy` ou `get_store_information`.
- Perguntas fora do escopo não poderão acionar ferramentas de dados.
- Intenção ambígua deverá produzir pergunta de esclarecimento antes da consulta.

### 12.5 Guardrails das ferramentas

- Todas as entradas serão validadas por modelos Pydantic com modo estrito.
- Campos inesperados serão rejeitados.
- Enums serão usados para status, categoria de informação e forma de pagamento.
- Limites numéricos, tamanhos e quantidades serão aplicados no servidor.
- O LLM nunca fornecerá SQL, caminho de arquivo ou nome de tabela.
- Consultas utilizarão parâmetros, nunca interpolação de strings.
- O banco utilizado pelo agente será aberto em modo somente leitura.
- Cada ferramenta retornará somente os campos necessários ao caso de uso.
- Erros internos serão convertidos em códigos seguros; stack traces não serão enviados ao modelo.

Limites por turno:

- Máximo de 4 ciclos de function calling.
- Máximo de 8 chamadas de ferramenta.
- Tempo limite de 5 segundos por ferramenta local.
- Uma única tentativa de regeneração quando a resposta falhar na validação.

### 12.6 Guardrails determinísticos de negócio

As seguintes decisões nunca serão delegadas ao LLM:

- Disponibilidade: `status == "active"` e `stock_quantity > 0`.
- Validade da promoção: `is_active == true`.
- Cálculo monetário com `Decimal` e arredondamento em duas casas.
- Não cumulatividade entre promoção e desconto de PIX.
- Regras de quantidade e valor mínimo das parcelas.
- Validação do pedido por número e identificador do cliente.
- Mascaramento de dados pessoais.
- Precedência entre dados estruturados e políticas.

O LLM poderá explicar o resultado, mas não alterá-lo.

### 12.7 Guardrails de contexto

- O histórico será limitado às 12 mensagens mais recentes da sessão.
- Resultados brutos extensos não permanecerão no contexto.
- Dados pessoais serão removidos do contexto assim que a consulta terminar.
- Valores dinâmicos mencionados anteriormente não serão reutilizados sem nova consulta.
- Mensagens do usuário, resultados de ferramentas e instruções do sistema serão enviados em papéis separados.
- Conteúdo do PDF e dos CSVs será tratado como dado, nunca como instrução.
- O histórico não será compartilhado entre sessões.

### 12.8 Contrato de resposta fundamentada

Antes de chegar à interface, a resposta deverá obedecer ao contrato interno:

```text
GroundedResponse
  answer: str
  skill: str
  evidence_refs: list[EvidenceRef]
  requires_human: bool
  limitation: str | null

EvidenceRef
  source_type: "tool" | "policy"
  source_id: str
  tool_call_id: str | null
  chunk_id: str | null
```

Regras:

- Toda afirmação verificável sobre produto, preço, estoque, promoção, pedido, prazo, contato ou política deverá possuir uma evidência.
- Referências devem apontar para uma chamada executada no turno atual ou para um chunk recuperado.
- Números, datas, percentuais, valores monetários e códigos serão comparados com as evidências.
- A resposta não poderá introduzir produtos ou pedidos ausentes do retorno das ferramentas.
- Uma resposta sem evidência obrigatória será descartada.
- O metadado interno não será exibido integralmente ao cliente.

### 12.9 Validação da saída

O validador executará, nesta ordem:

1. Validação estrutural do `GroundedResponse`.
2. Verificação de que as ferramentas citadas foram realmente executadas.
3. Verificação de que IDs de chunks existem no resultado do RAG.
4. Comparação de números e códigos presentes na resposta com as fontes.
5. Busca por exposição indevida de telefone, e-mail ou dados cadastrais.
6. Verificação de citações obrigatórias em respostas de políticas.
7. Verificação de promessas de ações que o sistema não pode executar.

Se a saída falhar:

1. Será permitida uma regeneração com os erros de validação.
2. Se falhar novamente, será retornado um fallback seguro.

### 12.10 Guardrails contra alucinação

- Temperatura padrão baixa (`0.1`), quando suportada pelo modelo.
- Instrução explícita para não responder por memória sobre dados da loja.
- Uso obrigatório das ferramentas para fatos verificáveis.
- Resultados pequenos e relevantes, reduzindo distração contextual.
- Citações para políticas e rastreabilidade interna para todas as demais afirmações.
- Sem acesso a busca web ou fontes não autorizadas.
- Sem ferramenta genérica de banco, arquivos ou execução de código.
- Sem preenchimento automático de campos ausentes.
- Sem inferência de prazo com base apenas no status do pedido.
- Sem recomendação de produto indisponível como opção de compra.

### 12.11 Fallbacks seguros

Respostas padrão serão usadas quando:

- Não houver evidência suficiente.
- Uma ferramenta falhar.
- A identidade do cliente não for validada.
- As fontes apresentarem conflito não resolvido.
- O limite de chamadas for atingido.
- A saída falhar duas vezes na validação.

O fallback deverá explicar a limitação sem inventar causa, dado ou prazo e indicar o atendimento humano quando apropriado.

### 12.12 Testes dos guardrails

Serão incluídos testes para:

- Pedido de preço sem chamada de ferramenta.
- Tentativa de sobrescrever o prompt.
- Solicitação para executar SQL ou revelar clientes.
- Dados de pedido com identidade incorreta.
- Produto inexistente ou indisponível.
- Promoção inativa solicitada como válida.
- Política sem evidência recuperada.
- Número ou valor alterado na resposta.
- Citação de chunk inexistente.
- Exposição de telefone ou e-mail.
- Excesso de ciclos de ferramentas.
- Falha simultânea do LLM e da ferramenta.

## 13. Recuperação das políticas

### 13.1 Escopo do RAG

O RAG será usado exclusivamente para conteúdo normativo e institucional presente em `políticas_da_loja.pdf`.

Não serão indexados no RAG:

- Produtos, preços ou estoque.
- Clientes, pedidos ou rastreamento.
- Promoções.
- O SDD.
- Histórico da conversa.

Esses dados possuem contratos estruturados e serão acessados pelas ferramentas determinísticas.

### 13.2 Pipeline de ingestão

1. Calcular o checksum do PDF.
2. Extrair o texto página por página com `pypdf`.
3. Normalizar espaços e quebras sem alterar o significado.
4. Identificar títulos e subtítulos numerados.
5. Criar chunks sem atravessar limites de seção.
6. Gerar uma representação normalizada para busca.
7. Construir o índice BM25.
8. Persistir índice e manifesto em `data/processed/`.

Negativas como “não”, números, percentuais, prazos e valores monetários não serão removidos durante a normalização.

### 13.3 Estratégia de chunking

- Unidade preferencial: subseção completa.
- Tamanho alvo: entre 300 e 700 tokens.
- Tamanho máximo: 900 tokens.
- Sobreposição: 60 tokens somente quando uma subseção precisar ser dividida.
- Um chunk nunca deverá combinar políticas de seções diferentes.
- O título hierárquico será repetido em cada chunk.

### 13.4 Contrato de ingestão

Cada trecho deverá obedecer ao seguinte contrato:

```text
PolicyChunk
  chunk_id: str
  document_id: str
  source_file: str
  document_version: str
  section_number: str
  section_title: str
  page_start: int
  page_end: int
  content: str
  normalized_content: str
  checksum: str
```

Restrições:

- `content` não pode estar vazio.
- Páginas devem ser positivas e ordenadas.
- `checksum` deve permitir detectar mudança da fonte.
- `document_version` será `2.1`, conforme o manual.
- O conteúdo original deverá ser preservado para citação.

### 13.5 Contrato de consulta

Entrada de `search_store_policy`:

```text
PolicySearchQuery
  topic: str              # entre 3 e 500 caracteres
  limit: int = 3          # mínimo 1, máximo 5
```

Processamento:

- Normalizar caixa, acentos e pontuação.
- Expandir apenas sinônimos de domínio previamente definidos.
- Executar BM25 sobre título hierárquico e conteúdo.
- Priorizar correspondência no título, sem excluir o conteúdo.
- Retornar no máximo cinco evidências.

O dicionário inicial de domínio incluirá relações como:

- devolução, arrependimento e reembolso;
- troca, defeito e preferência;
- entrega, frete, envio e rastreamento;
- pagamento, PIX, cartão, boleto e parcelamento;
- horário, funcionamento e expediente;
- privacidade, dados pessoais e LGPD.

### 13.6 Contrato de retorno

```text
PolicySearchResult
  found: bool
  query: str
  evidences: list[PolicyEvidence]

PolicyEvidence
  chunk_id: str
  section_number: str
  section_title: str
  page_start: int
  page_end: int
  excerpt: str
  score: float
  source_file: str
  document_version: str
```

Regras:

- `found` será falso quando não houver sobreposição lexical significativa.
- `score` servirá para ordenação e diagnóstico, não como probabilidade.
- `excerpt` deverá conter somente texto da fonte.
- O retorno não conterá instruções para o agente além dos dados da política.

### 13.7 Contrato de resposta fundamentada

Para uma resposta sobre políticas, o agente deverá:

1. Usar somente evidências retornadas com `found = true`.
2. Responder à pergunta sem copiar conteúdo excessivo.
3. Citar seção e página no formato “Política 4.1, página 4”.
4. Distinguir regra confirmada de condição ainda não informada.
5. Solicitar contexto adicional quando necessário.
6. Encaminhar ao atendimento humano quando não houver evidência suficiente.

O agente não poderá usar conhecimento prévio do modelo para completar políticas ausentes.

### 13.8 Precedência das fontes

Em caso de conflito:

1. SQLite prevalece para preço, estoque, promoção e pedido.
2. O PDF prevalece para políticas e informações institucionais.
3. Uma subseção específica do PDF prevalece sobre texto geral.
4. O SDD descreve o sistema, mas não é fonte de regra comercial.
5. A conversa fornece contexto, mas não altera dados ou políticas.
6. Conhecimento interno do LLM nunca prevalece sobre as fontes.

Conflitos ainda não resolvidos deverão ser apresentados como limitação e encaminhados ao atendimento humano.

### 13.9 Proteções do RAG

- O PDF será tratado como conteúdo, não como instrução de sistema.
- Somente o arquivo explicitamente autorizado será indexado.
- O índice será reconstruído quando o checksum mudar.
- A saída será limitada em tamanho.
- Não haverá recuperação de dados pessoais.
- Conteúdo recuperado não poderá habilitar novas ferramentas.

### 13.10 Avaliação do RAG

Será criado um conjunto de perguntas com evidências esperadas para:

- Horário e endereço.
- Formas de pagamento e parcelamento.
- Direito de arrependimento.
- Troca por defeito e por preferência.
- Garantia legal.
- Frete local e para outras cidades.
- Promoções e não cumulatividade.
- Privacidade e exclusão de dados.
- Escopo do catálogo.

Métricas mínimas:

- `Recall@3` das seções esperadas.
- Taxa de respostas com citação válida.
- Taxa de respostas sem suporte documental.
- Casos corretamente encaminhados por ausência de evidência.

A primeira versão usará BM25. Embeddings somente serão adicionados se os testes demonstrarem ganho mensurável.

## 14. Tratamento de erros

| Situação | Comportamento |
|---|---|
| Produto não encontrado | Informar e solicitar mais detalhes. |
| Produto sem estoque | Informar indisponibilidade e buscar alternativas. |
| Pedido não encontrado | Não confirmar a existência de dados; solicitar revisão das informações. |
| Falha de validação do cliente | Não revelar o pedido. |
| Política não localizada | Informar a limitação e encaminhar ao atendimento humano. |
| Falha do provedor | Retornar mensagem segura para nova tentativa. |
| Dados inconsistentes | Não corrigir por suposição; usar o dado confiável disponível ou encaminhar. |

## 15. Observabilidade

Serão registrados:

- Identificador anônimo da sessão.
- Tipo de intenção detectada.
- Nome da ferramenta chamada.
- Duração e sucesso da chamada.
- Categoria do erro.
- Quantidade de tokens, quando fornecida pelo provedor.

Não serão registrados prompts completos contendo dados pessoais.

## 16. Estratégia de testes

### 16.1 Testes unitários

- Disponibilidade de produtos.
- Aplicação de promoções.
- Não cumulatividade com PIX.
- Regras de parcelamento.
- Validação de identidade.
- Normalização de telefone e e-mail.
- Consulta e filtro de produtos.

### 16.2 Testes de integração

- Importação dos CSVs.
- Integridade dos relacionamentos.
- Execução das ferramentas sobre SQLite.
- Extração e busca das políticas.
- Ciclo de function calling com provedor simulado.

### 16.3 Avaliação conversacional

Cenários mínimos:

1. Violões disponíveis por até R$ 1.000,00.
2. Preço e disponibilidade do Takamine GD20.
3. Produto em promoção ativa com explicação da regra de PIX.
4. Pedido com autenticação válida e inválida.
5. Direito de arrependimento.
6. Produto esgotado com alternativa.
7. Solicitação de acessório fora do catálogo.
8. Pergunta completamente fora do escopo.
9. Tentativa de obter dados de outro cliente.
10. Instrução maliciosa presente na mensagem do usuário.

## 17. Estrutura proposta

```text
.
├── app.py
├── README.md
├── pyproject.toml
├── .env.example
├── artefatos_projeto/
│   ├── SDD.md
│   ├── desafio_tecnico_ai_eng_artefact.pdf
│   ├── políticas_da_loja.pdf
│   └── *.csv
├── data/
│   └── processed/
├── examples/
├── src/
│   └── emporio_agent/
│       ├── agent.py
│       ├── config.py
│       ├── database.py
│       ├── prompts.py
│       ├── models.py
│       ├── repositories/
│       ├── tools/
│       └── ingestion/
└── tests/
    ├── unit/
    ├── integration/
    └── evaluation/
```

## 18. Dados conhecidos e inconsistências

- O catálogo fornecido possui 65 produtos, apesar de o manual mencionar mais de 300.
- Existem produtos ativos com estoque zero.
- Existem produtos `coming_soon` com estoque preenchido.
- Alguns produtos entre os IDs 135 e 144 possuem divergências entre nome, descrição e especificações.
- O manual apresenta um telefone geral e outro número específico para WhatsApp.
- Há divergência textual entre a regra geral e as regras detalhadas de parcelamento.
- Não há período inicial e final para promoções.
- Não há informação explícita sobre a data de referência dos dados.

Essas divergências não serão corrigidas silenciosamente. As suposições adotadas serão documentadas no README e protegidas por regras determinísticas.

## 19. Critérios de aceite

- O projeto inicia com instruções documentadas.
- O chat responde usando o tom definido.
- Consultas de catálogo refletem os CSVs.
- Preços e promoções são calculados corretamente.
- Produtos indisponíveis não são anunciados como disponíveis.
- Pedidos não são revelados sem validação.
- Perguntas de políticas são fundamentadas no manual.
- O agente não inventa resposta quando uma ferramenta falha.
- Os testes críticos passam.
- O repositório contém entre 3 e 5 exemplos de conversa.

## 20. Decisões técnicas consolidadas

1. OpenAI será o provedor de referência e `gpt-4.1-mini` o modelo padrão configurável.
2. O ciclo de function calling será implementado diretamente com o SDK oficial.
3. As políticas usarão busca lexical BM25 na primeira versão.
4. Streamlit será a interface final de demonstração.
5. O histórico permanecerá apenas na sessão e não será armazenado permanentemente.
6. SQLite será usado como base local somente leitura durante o atendimento.
7. O LLM não terá acesso direto a SQL, arquivos, clientes ou execução de código.

## 21. Evoluções futuras

- Integração real com WhatsApp.
- API FastAPI para múltiplos canais.
- Banco PostgreSQL.
- Busca híbrida lexical e vetorial.
- Painel de avaliação e observabilidade.
- Atendimento humano com transferência de contexto.
- Autenticação robusta para consultas de pedidos.
- Sincronização em tempo real com sistemas de estoque e logística.
