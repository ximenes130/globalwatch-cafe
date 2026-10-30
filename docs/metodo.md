# Método em detalhe: calibração, conferências e imagem adicional

Complemento da [nota de pesquisa](nota-de-pesquisa.md), que cabe em duas páginas. Aqui ficam
as tabelas, os números por classe e as figuras. Specs de origem: 002 (método e calibração),
003 (imagem adicional) e 007 (inspeção visual).

## Cascata de exclusões (`spectral-rules-1.1`)

| Nível | Regra | Área excluída no kit |
| --- | --- | --- |
| N0 | NoData (DN = 0 em qualquer banda) | 0,00 ha |
| N1 | Máscara de qualidade: SCL 0, 1, 3, 6, 8, 9, 10 e 11; sem SCL, NDWI ≥ 0 | 0,00 ha |
| N2 | NDVI < 0,55 (solo exposto, pasto seco) | 1.279,76 ha |
| N3 | NDVI > 0,72 (dossel fechado de mata e eucalipto) | 870,46 ha |
| N3b | GNDVI mínimo: desligado (`gndvi_min = null`) | 0,00 ha |
| N3c | Amplitude de NDVI ≥ 0,25 entre duas datas (só com a segunda data) | 0,00 ha |
| N4 | Abertura e fechamento (1 iteração) e manchas < 0,5 ha | 256,68 ha |
| | **Área potencial** | **214,54 ha** (124 polígonos) |

Soma: 214,54 + 1.279,76 + 870,46 + 256,68 = 2.621,44 ha, a área total do kit (512 x 512 px de
100 m²). A área é contada em pixels no CRS UTM do arquivo (EPSG:32723), antes de qualquer
reprojeção. A conversão de DN para reflectância (`DN × 0,0001 − 0,1`, das tags do arquivo) é
feita uma única vez, na leitura.

Os parâmetros e a `method_version` são gravados com cada análise (`analyses.params`). Toda
análise antiga pode ser refeita com os mesmos valores.

## Exploração e calibração (T2.5)

Script: `scripts/calibrate_thresholds.py`. Figuras em `evidencias/calibracao/`.

- O NDVI do kit tem dois picos: um em ~0,30 (pasto seco e solo em agosto) e outro em ~0,78
  (dossel denso). Histograma: `evidencias/calibracao/histogramas.png`.
- A SCL do kit só tem as classes 2, 4, 5 e 7; a máscara de qualidade não remove pixels neste
  recorte.
- NDVI e GNDVI nos pixels de vegetação têm r = 0,96. Numa data única o GNDVI repete o NDVI,
  por isso é calculado e reportado, mas não vira condição.

### Erro encontrado: teto do NDVI

A faixa de partida, NDVI de 0,55 a 0,78, marcava como candidato boa parte do interior da mata
e das bordas dos fragmentos. Em amostras delimitadas olhando a imagem:

| Variante | Núcleo da mata como candidato | Talhões em nível como candidato | Candidato antes da morfologia |
| --- | --- | --- | --- |
| Teto 0,78 (inicial) | 38% | 74% a 77% | 801 ha |
| Teto 0,72 (final) | 7% | 60% a 64% | 457 ha |

O NDVI do núcleo da mata vai de 0,71 (p5) a 0,84 (p95), e o dos talhões de 0,44 a 0,77: as
faixas se sobrepõem, e o teto de 0,72 troca falso positivo de mata por omissão de café
vigoroso. Uma regra extra de vermelho mínimo separava um pouco melhor, mas foi recusada por ser
um limiar empírico sem referência (`mascara-alternativa-vermelho-040.jpg`).

Figuras de antes e depois: `evidencias/calibracao/mascara-inicial.jpg` e `mascara-final.jpg`.
Os percentuais comparam variantes sobre amostras escolhidas à mão; não são acurácia.

## Conferência com o MapBiomas (T2.5)

Depois da decisão, a faixa foi conferida com o MapBiomas 2024 (Coleção 10, 30 m), sem ajustar
os limiares a ele. É concordância com outro produto, que tem resolução, data e erros próprios;
não é acurácia.

| Medida | Teto 0,78 | Teto 0,72 |
| --- | --- | --- |
| Formação Florestal marcada como candidato (antes da morfologia) | 42% | 13% |

Com a regra completa (área potencial de 214,54 ha):

- a classe Café do MapBiomas tem 49 ha no recorte, com NDVI mediano de 0,63, próximo dos
  talhões delimitados na imagem (0,64); 48% dela fica na faixa final, e o p95 de 0,79 mostra
  que café mais vigoroso fica de fora;
- 10% da área potencial cai em Café do MapBiomas, e 42% do Café dele fica marcado;
- a mata do MapBiomas marcada cai para 5%;
- o restante cai sobretudo em Mosaico de Usos, que pode conter café em talhões pequenos demais
  para 30 m, e em lavouras temporárias e cana, que uma imagem de agosto não separa de café.

Figuras: `evidencias/calibracao/mapbiomas-inicial.jpg` e `mapbiomas-final.jpg`.

**Licença.** A página de termos de uso do MapBiomas declara CC BY-SA 4.0; o rodapé da página de
downloads aponta CC BY 4.0 (ambas consultadas em 30/10/2026). Seguimos a mais restritiva: as
figuras e tabelas derivadas do MapBiomas neste repositório ficam sob CC BY-SA 4.0, com a
citação "Projeto MapBiomas – Coleção 10 da Série Anual de Mapas de Cobertura e Uso da Terra do
Brasil, ano 2024". O raster foi lido do COG hospedado no Source Cooperative, que também declara
CC BY-SA 4.0; o MapBiomas não é redistribuído aqui.

## Imagem adicional: estação chuvosa (spec 003)

Script: `scripts/download_additional_scene.py` (busca, escolha e download no formato do kit) e
`scripts/compare_dates.py` (comparação). Figura e tabelas: `evidencias/comparacao-datas/`.

A cena `S2B_T23KLS_20260110T131730_L2A` (10/01/2026) tem a mesma órbita e a mesma grade do kit.
Ela foi escolhida entre 55 cenas de dezembro a março por não ter nuvem, sombra nem sem-dado
dentro do recorte, e foi processada com o mesmo pipeline e os mesmos parâmetros.

| Medida | Kit (16/08/2025) | Janeiro (10/01/2026) |
| --- | --- | --- |
| NDVI mediano do recorte | 0,56 | 0,86 |
| Área potencial | 214,54 ha (124 polígonos) | 139,12 ha (75 polígonos) |

As duas datas têm só 10,11 ha de área potencial em comum. Na chuva, 191 ha da área potencial da seca passam do teto de 0,72, e o que entra no lugar é
sobretudo pasto verde: 83 dos 129 ha que só aparecem na chuva são Pastagem no MapBiomas. Os
limiares valem para a seca; um arquivo da estação chuvosa gera área potencial dominada por
pasto.

### Amplitude entre as datas

A amplitude |ΔNDVI| por classe do MapBiomas segue o que Souza et al. (2019) descrevem:

| Classe do MapBiomas | Amplitude mediana (recorte) | Dentro da área potencial da seca |
| --- | --- | --- |
| Formação florestal | 0,12 | 0,20 |
| Café | 0,15 | 0,16 |
| Mosaico de usos | 0,21 | 0,19 |
| Pastagem | 0,36 | 0,20 |
| Lavouras temporárias | 0,39 | 0,24 |
| Cana | 0,54 | 0,28 |

Dentro da área potencial as classes se sobrepõem: a faixa de agosto já tirou a maior parte do
pasto, e a segunda data separa sobretudo lavoura temporária e cana.

A app aceita a segunda data como entrada opcional e remove o pixel cuja amplitude chega a 0,25,
a oscilação de pico a pico do pasto em Souza et al. (2019). O limiar não foi escolhido pelo
histograma, que não tem vale entre as classes, nem pelo MapBiomas, para a conferência não
ficar circular.

| Medida | Só o kit | Kit + janeiro |
| --- | --- | --- |
| Área potencial | 214,54 ha (124 polígonos) | 103,04 ha (68 polígonos) |
| Excluído pela amplitude (N3c) | — | 101,78 ha |
| Área potencial em Café do MapBiomas | 10% | 17% |
| Café do MapBiomas marcado | 42% | 35% |

A regra também corta parte do que o MapBiomas chama de café.

## Inspeção visual (T7.1)

15 pontos sorteados com semente fixa sobre o resultado do kit: 10 na área potencial, 3 em
dossel denso e 2 em NDVI baixo. Prancha, coordenadas e leitura ponto a ponto em
[`evidencias/inspecao/inspecao-visual.md`](evidencias/inspecao/inspecao-visual.md).

- Área potencial: 3 pontos com aparência de lavoura em fileiras (2 com talhões em curva de
  nível), 4 indefinidos e 3 que provavelmente não são café (clareira na mata, verde irrigado,
  borda de mata).
- Exclusões: 4 coerentes (mata e solo) e 1 possível talhão de menor vigor deixado de fora.
- Erro recorrente: pixels de borda de mata, que misturam copa e pasto ou solo e caem na faixa
  de NDVI.

## Verificação em produção

Os mesmos números saem da aplicação publicada: kit, cena de janeiro e kit com segunda data, em
`evidencias/producao.md`.
