# Nota de pesquisa — áreas potenciais de café

30/10/2026 · Detalhes, tabelas e figuras em [`metodo.md`](metodo.md).

## 1. Problema e abordagem

O kit é um recorte Sentinel-2 L2A de 512 x 512 px (10 m, EPSG:32723) perto de Guaxupé/MG, de
16/08/2025, com azul, verde, vermelho e NIR e sem rótulo de café. Com uma data e sem gabarito
não dá para afirmar onde há café; dá para indicar **áreas potenciais**: vegetação cujo
comportamento espectral na seca é compatível com café em produção. Em agosto o pasto seca e o
NDVI dele cai, enquanto o café, perene, mantém o vigor (Maskell et al., 2021, usam a mesma
ideia com imagens da seca).

O método é uma cascata de exclusões com limiares explícitos, inspirada na classificação
hierárquica de Parreiras et al. (2025). Lá cada nível é um classificador treinado; aqui é uma
regra auditável: (1) NoData e pixels ruins pela SCL (ou NDWI, sem SCL); (2) NDVI < 0,55, solo
e pasto seco; (3) NDVI > 0,72, dossel fechado; (4) GNDVI só se mostrasse ganho (não mostrou);
(5) morfologia e manchas < 0,5 ha. Cada nível registra os hectares que tirou, e a
justificativa do mapa e do chat sai desses números. Uma segunda data opcional remove pixels cuja
amplitude de NDVI chega a 0,25.

## 2. Fontes primárias

- **Parreiras et al. (2025)**, metodologia de mapeamento de café em níveis (HLS denso e Random
  Forest/XGBoost, Caconde/SP). Dela vêm a estrutura em cascata, o GNDVI (39% da importância das
  variáveis para separar perenes) e o alerta de que eucalipto se confunde com café sem SWIR.
- **Maskell et al. (2021)**, café no Vietnã com Sentinel-2 de seca e chuva, Sentinel-1 e
  relevo: 89% de acurácia global, mas 56% a 71% de acurácia de usuário nas classes de café. É o
  teto do que se espera mesmo com dados mais ricos que o kit.
- **Souza et al. (2019)**, séries de NDVI no sul de Minas: o componente sazonal do café varia
  menos que o do pasto e perto do da mata. Base da regra de amplitude entre duas datas.
- **Gitelson, Kaufman e Merzlyak (1996)**, GNDVI; **McFeeters (1996)**, NDWI.

## 3. Alternativas consideradas

1. **Random Forest treinado com amostras do MapBiomas** (linha de Maskell e Parreiras).
   Recusada: o kit não tem rótulos, as amostras herdariam os erros de um produto de 30 m, e
   comparar o resultado com o próprio MapBiomas viraria verificação circular.
2. **Modelo pronto Coffee Probability 2026a** (Forest Data Partnership), probabilidade de café
   a 10 m. Recusada como classificador: roda no Earth Engine sobre embeddings anuais, não sobre
   o arquivo enviado, exige conta e cobre 2018 a 2024.

**Escolha: regras espectrais versionadas.** Processa o arquivo enviado, é reproduzível
(`params` e `method_version` salvos por análise) e explicável linha a linha. O custo é a
capacidade de separar café de outras perenes de vigor parecido.

## 4. Dados e modelos: origem e condições de uso

| Item | Origem | Condição de uso (conferida em 30/10/2026) |
| --- | --- | --- |
| Kit e cena de 10/01/2026 | Sentinel-2 L2A, Earth Search (Element 84) | Sentinel Data Legal Notice: uso livre, com "Contains modified Copernicus Sentinel data" |
| MapBiomas Col. 10 (2024) | COG no Source Cooperative | Só conferência; CC BY-SA 4.0 nos termos (o rodapé de downloads diz CC BY 4.0: seguimos a mais restritiva) |
| LLM | Claude Haiku 5.5, API da Anthropic | Termos comerciais: a Anthropic não treina com o conteúdo enviado pela API |
| Basemap | OpenFreeMap sobre OpenStreetMap | Gratuito, sem chave; atribuição OpenFreeMap, © OpenMapTiles e © OpenStreetMap no mapa |
| Coffee Probability 2026a | Forest Data Partnership | Considerado e não usado; CC BY 4.0 |

## 5. Verificação, erro encontrado e limitações

**Verificação.** (a) Sanidade de área: a soma da área potencial com as exclusões dá os
2.621,44 ha do kit (214,54 ha potenciais em 124 polígonos), calculados em UTM; os mesmos
números saem da app publicada. (b) Inspeção visual de 15 pontos sorteados: dos 10 potenciais,
3 parecem lavoura em fileiras, 4 são indefinidos e 3 provavelmente não são café; das 5
exclusões, 4 são coerentes. (c) Concordância com o MapBiomas, sem ajustar limiares a ele: 10%
da área potencial cai em Café do MapBiomas, e 42% do Café dele fica marcado. Nada disso é
acurácia.

**Erro encontrado.** A faixa de partida (NDVI 0,55 a 0,78) marcava boa parte da mata: em
amostras delimitadas na imagem, 38% do núcleo da mata virava candidato. O NDVI da mata vai de
0,71 a 0,84 e o dos talhões de 0,44 a 0,77. O teto baixou para 0,72: a mata marcada caiu para
7% (no MapBiomas, Formação Florestal de 42% para 13%), ao custo de omitir café mais vigoroso.
Antes e depois: `evidencias/calibracao/mascara-inicial.jpg` e `mascara-final.jpg`.

**Imagem adicional.** Com a cena de janeiro sozinha, a área potencial vira 139,12 ha, só
10,11 ha em comum com a seca, dominada por pasto verde: os limiares valem para a seca. Com as
duas datas, a amplitude tira 101,78 ha (sobretudo lavoura temporária e cana) e a área cai para
103,04 ha.

**Limitações.**

- Uma ou duas datas não são série temporal: o método não separa café de outras perenes, pasto
  irrigado ou capoeira com NDVI parecido, nem de mata pela amplitude.
- Pixels de borda de mata misturam copa e pasto e caem na faixa (visto na inspeção).
- Sem SWIR, café e eucalipto se separam só pelo teto de NDVI, que também corta café adensado.
- Café jovem, podado ou recepado fica abaixo do piso de 0,55.
- Limiares calibrados no próprio kit, da seca e de uma região; podem não valer em outra.
- Sem gabarito de campo: o resultado é "área potencial", `validated: false`, sem acurácia.

## Referências

1. Parreiras, T. C. et al. Dense time series of harmonized Landsat Sentinel-2 and ensemble
   machine learning to map coffee production stages. *Remote Sensing*, 17(18), 3168, 2025.
   doi:10.3390/rs17183168
2. Maskell, G. M. et al. Integration of Sentinel optical and radar data for mapping smallholder
   coffee production systems in Vietnam. *Remote Sensing of Environment*, 266, 112709, 2021.
   doi:10.1016/j.rse.2021.112709
3. Souza, C. G. et al. Variáveis multitemporais para o mapeamento de áreas de cultivo de café.
   *Pesquisa Agropecuária Brasileira*, 54, 2019. doi:10.1590/S1678-3921.pab2019.v54.00017
4. Gitelson, A. A.; Kaufman, Y. J.; Merzlyak, M. N. Use of a green channel in remote sensing of
   global vegetation from EOS-MODIS. *Remote Sens. Environ.*, 58(3), 289–298, 1996.
   doi:10.1016/S0034-4257(96)00072-7
5. McFeeters, S. K. The use of the Normalized Difference Water Index (NDWI) in the delineation
   of open water features. *Int. J. Remote Sens.*, 17(7), 1425–1432, 1996.
   doi:10.1080/01431169608948714
6. Forest Data Partnership. Coffee Probability model 2026a, Google Earth Engine, acesso em
   30/10/2026.
7. Projeto MapBiomas – Coleção 10 da Série Anual de Mapas de Cobertura e Uso da Terra do
   Brasil, ano 2024, acesso em 30/10/2026.
