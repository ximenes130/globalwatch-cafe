# Nota de pesquisa — áreas potenciais de café

Até duas páginas. Requisitos: [spec 007](../specs/007-documentacao-entrega/requirements.md) (R7.4–R7.8).
Só cite o que foi aberto e conferido.

## 1. Problema e abordagem

O kit traz um recorte Sentinel-2 L2A de 512 x 512 px (10 m, EPSG:32723) no
entorno de Guaxupé/MG, adquirido em 16/08/2025. Ele tem quatro bandas (azul,
verde, vermelho e NIR) e nenhum rótulo de café. Com uma data e sem gabarito, a
aplicação não pode afirmar onde há café. Ela pode indicar **áreas potenciais**:
vegetação cujo comportamento espectral é compatível com café em produção na
estação seca.

A abordagem é uma cascata de exclusões com limiares explícitos, inspirada na
classificação hierárquica de Parreiras et al. (2025). Lá, cada nível é um
classificador treinado. Aqui, cada nível é uma regra auditável:

1. Remover NoData e pixels ruins pela máscara de qualidade (SCL ou NDWI).
2. Remover NDVI baixo: solo exposto e pasto seco.
3. Remover NDVI alto: dossel fechado de mata e eucalipto.
4. Aplicar o GNDVI como condição extra, só se a calibração mostrar ganho.
5. Limpar com morfologia e descartar manchas menores que 0,5 ha.

O restante vira polígonos, com área calculada em UTM. Cada nível registra os
hectares que excluiu, e a justificativa mostrada na UI e no chat sai desses
números.

A data de agosto favorece o método. Na seca o pasto senesce e o NDVI dele cai,
enquanto o café, perene e sempre-verde, mantém o vigor. Maskell et al. (2021)
partem da mesma hipótese: imagens da seca capturam melhor a diferença de
folhagem entre culturas arbóreas. Em Parreiras et al. (2025), julho está entre
os meses mais importantes para separar culturas perenes de pasto.

## 2. Fontes primárias

- **Parreiras et al. (2025)** é a metodologia de mapeamento de café usada como
  referência. Os autores classificam em níveis, com série densa HLS e Random
  Forest/XGBoost, em Caconde/SP: vegetação antrópica, depois perenes contra
  pasto e cultura anual, depois café contra silvicultura e, por fim, os
  estágios do café. Achados que usamos:
  - GNDVI foi o índice mais importante para separar perenes; com a banda
    verde, respondeu por 39% da importância das variáveis.
  - O eucalipto se confunde espectralmente com o café; a separação dependeu de
    SWIR e do ano inteiro.
  - A textura GLCM teve importância média menor que bandas e índices.
- **Maskell et al. (2021)** mapearam café no Vietnã com composições Sentinel-2
  de seca e chuva, Sentinel-1 e relevo. O mapa café/não café teve 89% de
  acurácia global. A acurácia de usuário foi de 65% para café a pleno sol, 56%
  para consorciado e 71% para jovem. Esses números mostram o limite do que se
  pode esperar mesmo com dados mais ricos que os do kit.
- **Souza et al. (2019)** estudaram séries de NDVI no sul de Minas. O
  componente sazonal do café (−0,05 a 0,06) varia menos que o do pasto (−0,15
  a 0,10), mas fica próximo ao da vegetação nativa (−0,04 a 0,08). Isso
  fundamenta a regra de duas datas da imagem adicional e mostra que essa regra
  não separa café de mata.
- **Gitelson, Kaufman e Merzlyak (1996)** propõem o GNDVI: a banda verde é
  mais sensível à clorofila que o vermelho.
- **McFeeters (1996)** define o NDWI (verde e NIR), usado como máscara de água
  quando a SCL não é enviada.

## 3. Alternativas consideradas e escolha

**Alternativa 1: classificador supervisionado (Random Forest) treinado com
amostras do MapBiomas.** É a linha de Maskell et al. (2021) e de Parreiras et
al. (2025). Foi recusada por três motivos:

- O kit não tem rótulos.
- Amostras tiradas do MapBiomas (classe 46, Café, 30 m, Landsat) herdariam os
  erros desse produto.
- Comparar o resultado com o próprio MapBiomas viraria uma verificação
  circular.

O ganho de acurácia também não teria como ser medido sem gabarito.

**Alternativa 2: usar um modelo pronto, o Coffee Probability 2026a da Forest
Data Partnership.** É uma probabilidade de café por pixel, a 10 m, com dados
de referência digitalizados no Brasil. Foi recusada como classificador da
aplicação por três motivos:

- O modelo roda no Google Earth Engine sobre embeddings anuais (AlphaEarth),
  não sobre o arquivo enviado. Isso viola a exigência de processar o upload.
- Exige conta no Earth Engine.
- Cobre 2018 a 2024; o kit é de 2025.

O modelo continua útil como produto independente de comparação, fora da
aplicação.

**Escolha: regras espectrais com parâmetros versionados.** Esse método:

- processa o arquivo enviado de verdade;
- é reproduzível, porque `params` e `method_version` são salvos com cada
  análise;
- é explicável linha a linha;
- deixa claro, nível por nível, o que foi excluído.

O custo é a perda de capacidade discriminativa. Com uma data e sem SWIR, o
método não separa café de outras perenes com vigor parecido.

Medimos no kit a correlação entre NDVI e GNDVI nos pixels de vegetação:
r = 0,96. Numa data única, o GNDVI tende a repetir o NDVI. Por isso ele é
sempre calculado e reportado, mas só vira condição se a calibração mostrar
ganho visível.

## 4. Dados e modelos: origem e condições de uso

- **Imagem do kit:** cena `S2B_T23KLS_20250816T132502_L2A`, catálogo Earth
  Search (Element 84), coleção `sentinel-2-c1-l2a`. Atribuição: "Contains
  modified Copernicus Sentinel data (2025)". Os termos são os do Sentinel Data
  Legal Notice indicado em `data/exemplo/ATRIBUICAO.txt`, e a atribuição
  acompanha os dados no repositório.
- **Imagem adicional:** cena `S2B_T23KLS_20260110T131730_L2A`, de
  10/01/2026, com a mesma origem e as mesmas condições. Foi acessada em
  30/10/2026 por `scripts/download_additional_scene.py`, que grava a
  atribuição "Contains modified Copernicus Sentinel data (2026)" e os termos
  em `data/adicional/<item>/ATRIBUICAO.txt`.
- **Coffee Probability 2026a (Forest Data Partnership):** considerado e não
  usado na aplicação. A página do catálogo informa licença CC BY 4.0, com a
  atribuição "Produced by Google for the Forest Data Partnership". O próprio
  catálogo diz que é um conjunto comunitário que deve mudar.
- **MapBiomas:** só entra se a comparação P1 (R7.8) for feita, e então como
  concordância, não como acurácia.
  <!-- conferir os termos de uso no site oficial antes de citar a licença -->
- **LLM e basemap:** <!-- preencher nas specs 004 e 005 -->

## 5. Verificação, erro encontrado e limitações

**Verificação.**
<!-- PENDENTE (T2.5 e T2.7). Preencher com o que for medido:
  - sanidade de área: kit = 2.621,44 ha; total = potencial + soma das exclusões;
  - inspeção visual de 10 a 20 pontos sobre o RGB, descrita sem percentual;
  - histograma de NDVI com os limiares finais (docs/evidencias/). -->

Exploração preliminar do kit, feita antes da calibração:

- O NDVI tem dois picos: um em ~0,30, coerente com pasto seco e solo em
  agosto, e outro em ~0,78, de dossel denso.
- A faixa de partida de 0,55 a 0,78 abrange 801 ha (30,6% do recorte) antes da
  morfologia.
- A SCL do kit só tem as classes 2, 4, 5 e 7, então a máscara de qualidade não
  remove pixels neste recorte.

**Erro encontrado.**
A faixa de partida, NDVI de 0,55 a 0,78, marcava como candidato boa parte do
interior da mata e as bordas dos fragmentos. Em amostras delimitadas olhando a
imagem, 38% do núcleo da mata entrava, contra 74% a 77% dos talhões em curva
de nível. O NDVI do núcleo da mata vai de 0,71 (p5) a 0,84 (p95), e o dos
talhões de 0,44 a 0,77: as faixas se sobrepõem. O teto foi baixado para 0,72,
o que deixa 7% do núcleo da mata e 60% a 64% dos talhões, com 457 ha de
candidato antes da morfologia. Uma regra extra de vermelho mínimo separava um
pouco melhor, mas foi recusada por ser um limiar empírico sem referência.
Figuras de antes e depois: `docs/evidencias/calibracao/mascara-inicial.jpg` e
`mascara-final.jpg`. Os percentuais comparam variantes; não são acurácia.

Depois da decisão, a faixa foi conferida com o MapBiomas 2024 (Coleção 10,
30 m), sem ajustar os limiares a ele. Na classe Formação Florestal, o
candidato caiu de 42% para 13% com o teto de 0,72. A classe Café (49 ha no
recorte) tem NDVI mediano de 0,63, próximo dos talhões delimitados na imagem
(0,64), e 48% dela fica dentro da faixa final. O p95 de 0,79 mostra que café
mais vigoroso fica de fora. O MapBiomas é de 2024 e tem resolução e erros
próprios: o número é concordância, não acurácia.

Com a regra completa (abertura, fechamento e manchas de pelo menos 0,5 ha), a
área potencial do kit fica em 214,54 ha. Dessa área, 10% cai em café do
MapBiomas, e 42% do café dele fica marcado; a mata do MapBiomas marcada cai
para 5%. A maior parte do restante está em "Mosaico de Usos", que pode conter
café em talhões pequenos demais para 30 m, e em lavouras temporárias e cana,
que uma única imagem de agosto não separa de café. Figura:
`docs/evidencias/calibracao/mapbiomas-final.jpg`.

**Imagem adicional (chuva).** A cena de 10/01/2026 tem a mesma órbita e a
mesma grade do kit. Ela foi escolhida entre 55 cenas de dezembro a março por
não ter nuvem, sombra nem sem-dado dentro do recorte, e foi processada com o
mesmo pipeline e os mesmos parâmetros.

- A área potencial cai para 139,12 ha (75 polígonos). Só 10,11 ha coincidem
  com os 214,54 ha da seca.
- Na chuva, o NDVI mediano do recorte sobe de 0,56 para 0,86. Com isso, 191 ha
  da área potencial da seca passam do teto de 0,72.
- O que entra no lugar é sobretudo pasto verde: 83 dos 129 ha que só aparecem
  na chuva são Pastagem no MapBiomas.
- Conclusão: os limiares valem para a seca, e um arquivo da estação chuvosa
  gera área potencial dominada por pasto.

A amplitude |ΔNDVI| entre as datas segue o que Souza et al. (2019)
descrevem:

| Classe do MapBiomas | Amplitude mediana |
| --- | --- |
| Formação florestal | 0,12 |
| Café | 0,15 |
| Pastagem | 0,36 |
| Lavouras temporárias | 0,39 |
| Cana | 0,54 |

Dentro da área potencial da seca, porém, as classes se sobrepõem: café 0,16,
mosaico 0,19, pasto 0,20, mata 0,20, lavoura temporária 0,24 e cana 0,28. A
faixa de agosto já tirou a maior parte do pasto, e a segunda data separa
sobretudo lavoura temporária e cana.

A app aceita a segunda data como entrada opcional. Ela remove o pixel cuja
amplitude chega a 0,25, a oscilação de pico a pico do pasto em Souza et al.
(2019). O limiar não foi escolhido pelo histograma, que não tem vale entre as
classes, nem pelo MapBiomas, para a comparação não ficar circular.

- Com o kit e a cena de janeiro, a área potencial cai de 214,54 para
  103,04 ha (68 polígonos); a amplitude sozinha remove 101,78 ha.
- Na conferência posterior com o MapBiomas, a fração da área marcada que cai
  em café passa de 10% para 17%.
- O café do MapBiomas marcado cai de 42% para 35%: a regra também corta parte
  do que o MapBiomas chama de café.

Figura e tabelas: `docs/evidencias/comparacao-datas/`.

**Limitações.**

- **Uma ou duas datas.** Com uma data, o método não distingue café de outras
  perenes, pasto verde ou capoeira com NDVI parecido. A segunda data tira
  sobretudo cana e lavoura anual. Ela não separa café de mata, que também
  varia pouco (Souza et al., 2019), e duas imagens não são uma série
  temporal.
- **Sem SWIR.** O kit não traz SWIR, banda que Parreiras et al. (2025) usaram
  para separar café de eucalipto. Aqui essa separação depende só do teto de
  NDVI, que também corta café adensado ou sombreado.
- **Estágios de manejo.** Café recém-plantado, esqueletado ou recepado expõe
  solo e tende a ficar abaixo do piso de NDVI. Mesmo com Random Forest e
  radar, Maskell et al. (2021) obtiveram 71% de acurácia de usuário para café
  jovem e 56% para consorciado.
- **Limiares calibrados no próprio kit, que é da seca.** Na imagem de
  janeiro, os mesmos valores trocam quase toda a área potencial (só 10 ha em
  comum). Em outras regiões, os valores também podem não se aplicar.
- **Sem gabarito de campo.** O resultado é "área potencial de café", marcado
  como `validated: false`, sem acurácia ou confiança.

## Referências

1. Parreiras, T. C.; Santos, C. de O.; Bolfe, E. L.; Sano, E. E.; Leandro,
   V. B. S.; Bayma, G.; Silva, L. A. P. da; Furuya, D. E. G.; Romani, L. A. S.;
   Morton, D. Dense time series of harmonized Landsat Sentinel-2 and ensemble
   machine learning to map coffee production stages. *Remote Sensing*, 17(18),
   3168, 2025. <https://doi.org/10.3390/rs17183168>
2. Maskell, G. M.; Chemura, A.; Nguyen, H.; Gornott, C.; Mondal, P. Integration
   of Sentinel optical and radar data for mapping smallholder coffee production
   systems in Vietnam. *Remote Sensing of Environment*, 266, 112709, 2021.
   <https://doi.org/10.1016/j.rse.2021.112709>
3. Souza, C. G.; Arantes, T. B.; Carvalho, L. M. T. de; Aguiar, P. Variáveis
   multitemporais para o mapeamento de áreas de cultivo de café. *Pesquisa
   Agropecuária Brasileira*, 54, 2019.
   <https://doi.org/10.1590/S1678-3921.pab2019.v54.00017>
4. Gitelson, A. A.; Kaufman, Y. J.; Merzlyak, M. N. Use of a green channel in
   remote sensing of global vegetation from EOS-MODIS. *Remote Sensing of
   Environment*, 58(3), 289–298, 1996.
   <https://doi.org/10.1016/S0034-4257(96)00072-7>
5. McFeeters, S. K. The use of the Normalized Difference Water Index (NDWI) in
   the delineation of open water features. *International Journal of Remote
   Sensing*, 17(7), 1425–1432, 1996. <https://doi.org/10.1080/01431169608948714>
6. Forest Data Partnership. Coffee Probability model 2026a. Google Earth
   Engine, `projects/forestdatapartnership/assets/coffee/model_2026a`, acesso
   em 30/10/2026.
   <https://developers.google.com/earth-engine/datasets/catalog/projects_forestdatapartnership_assets_coffee_model_2026a>
