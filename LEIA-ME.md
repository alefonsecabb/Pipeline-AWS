# Dados para a avaliação prática

Dados inteiramente sintéticos. O calendário simulado inclui 2024–2026 completos; a inferência corresponde a janeiro de 2027. Cada versão representa uma rede independente.

CSV UTF-8, separador vírgula, aspas duplas quando necessário e cabeçalho. Campos vazios representam ausência. A qualidade e a disponibilidade temporal das variáveis devem ser avaliadas pela dupla.

Objetivo: estimar quantidade_vendida por dia, loja e produto. O estoque corresponde à abertura, o preço e a promoção são planejados e a temperatura é uma previsão prévia. A receita_final é apurada ao encerrar o dia.

Ingestão: separar no S3 os três históricos do arquivo de inferência, pois seus esquemas diferem. Não incluir README nos prefixos lidos como CSV.

## Dicionário
- **dataset_id**: Identificador da versão.
- **data**: Dia de referência; uma observação por loja/produto/dia antes das repetições.
- **loja**: Unidade da rede (4 lojas).
- **produto**: SKU (10 produtos, dois por categoria).
- **categoria**: Grupo comercial do produto.
- **preco**: Preço unitário planejado em reais, já com desconto da promoção.
- **promocao**: Indicador de promoção planejada: 0 ou 1.
- **estoque**: Unidades disponíveis no início do dia; conhecido antes da previsão.
- **quantidade_vendida**: Unidades vendidas no dia; variável a prever.
- **temperatura_prevista**: Previsão meteorológica em °C, disponível antes do dia de venda.
- **receita_final**: Faturamento efetivo apurado ao encerramento do dia, em reais.

Na inferência, quantidade_vendida não existe e receita_final está indisponível. Preservar dataset_id, data, loja e produto na saída de previsões.
