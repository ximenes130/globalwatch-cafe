import {
  type FilterSpecification,
  type GeoJSONSource,
  LngLatBounds,
  type LngLatLike,
  Map as MapLibre,
  type MapGeoJSONFeature,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef } from 'react'
import type { Corners, ResultUrls } from '@/lib/api'
import { formatHa, formatIndex } from '@/lib/format'
import { DURATION, easeOut, FLY_MS, prefersReducedMotion } from '@/lib/motion'

// O MapLibre procura o worker ao lado do próprio módulo, mas o bundler move o módulo:
// sem isto o worker não carrega (nem no `vite dev` nem no build) e o mapa fica vazio.
setWorkerUrl(workerUrl)

// Basemap vetorial gratuito, sem chave; a atribuição vem do próprio estilo (spec 004).
const BASEMAP = 'https://tiles.openfreemap.org/styles/positron'
const SENTINEL_ATTRIBUTION = 'Contém dados Copernicus Sentinel modificados'

// Cores de index.css: o MapLibre não lê variáveis CSS.
const CHERRY = '#b3122e'
const INK = '#14201a'

const LOCALE = {
  'NavigationControl.ZoomIn': 'Aproximar',
  'NavigationControl.ZoomOut': 'Afastar',
  'NavigationControl.ResetBearing': 'Voltar para o norte',
  'Popup.Close': 'Fechar',
  'AttributionControl.ToggleAttribution': 'Mostrar atribuição',
  'CooperativeGesturesHandler.WindowsHelpText': 'Use Ctrl + rolagem para aproximar o mapa',
  'CooperativeGesturesHandler.MacHelpText': 'Use ⌘ + rolagem para aproximar o mapa',
  'CooperativeGesturesHandler.MobileHelpText': 'Use dois dedos para mover o mapa',
}

export type Overlay = 'rgb' | 'classification'

/** Polígono pedido pelo card do chat (R5.15); `seq` repete o pedido para o mesmo id. */
export type Focus = { id: number; centroid: [number, number]; seq: number }

type Props = {
  corners: Corners
  urls: ResultUrls
  overlay: Overlay
  opacity: number
  /** A tela viu a análise processando: o mapa voa até a imagem (R4.19). */
  intro: boolean
  /** Chamado quando overlay e polígonos terminam de aparecer; o painel entra depois. */
  onRevealed: () => void
  focus: Focus | null
}

const FILL_OPACITY = 0.18

/**
 * Mapa com a imagem pelos 4 cantos, polígonos da área potencial e limite da imagem (R4.5, R4.7).
 *
 * Criado uma vez por análise (o pai usa `key={id}`): as URLs assinadas mudam a cada consulta
 * da API e não devem recriar o mapa. Camada e opacidade mudam pelo segundo efeito.
 *
 * Entrada (R4.19): voo até a imagem (só se `intro`), depois o overlay e por fim os polígonos,
 * por transições de pintura do próprio MapLibre. Com movimento reduzido, tudo instantâneo (R4.20).
 */
export default function MapView(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibre | null>(null)
  const popupRef = useRef<Popup | null>(null)
  const latest = useRef(props)
  const revealed = useRef(false)

  useEffect(() => {
    const { corners, urls, intro } = latest.current
    const reduced = prefersReducedMotion()
    const fly = intro && !reduced
    const transition = (delay = 0) => ({ duration: reduced ? 0 : DURATION.slow, delay: reduced ? 0 : delay })
    const bounds = corners.reduce((box, corner) => box.extend(corner), new LngLatBounds(corners[0], corners[0]))
    const narrow = window.matchMedia('(max-width: 1023px)').matches
    const map = new MapLibre({
      container: container.current!,
      style: BASEMAP,
      bounds,
      fitBoundsOptions: { padding: 32 },
      locale: LOCALE,
      attributionControl: { compact: true, customAttribution: SENTINEL_ATTRIBUTION },
      // No celular o mapa fica no meio da página: um dedo rola a página, dois movem o mapa.
      cooperativeGestures: narrow,
    })
    mapRef.current = map
    let disposed = false
    // Começa afastado para o voo ter de onde vir.
    if (fly) map.jumpTo({ zoom: map.getZoom() - 1.5 })
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')

    map.on('load', () => {
      // No celular a atribuição aberta cobre o mapa: fica recolhida no botão (i).
      if (narrow) container.current?.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')

      // Rasters abaixo dos rótulos do basemap; vetores por cima de tudo. Tudo começa transparente.
      const firstLabel = map.getStyle().layers.find((layer) => layer.type === 'symbol')?.id
      for (const [id, url] of [['rgb', urls.rgb_png], ['classification', urls.classification_png]] as const) {
        map.addSource(id, { type: 'image', url, coordinates: corners })
        map.addLayer(
          {
            id,
            type: 'raster',
            source: id,
            paint: {
              'raster-opacity': 0,
              'raster-opacity-transition': transition(),
              'raster-fade-duration': 0,
              'raster-resampling': 'nearest',
            },
          },
          firstLabel,
        )
      }
      applyOverlay(map, latest.current.overlay, 0)

      map.addSource('boundary', { type: 'geojson', data: boundary(corners) })
      map.addLayer({
        id: 'boundary',
        type: 'line',
        source: 'boundary',
        paint: { 'line-color': INK, 'line-width': 1.25, 'line-dasharray': [3, 2] },
      })

      map.addSource('potential', { type: 'geojson', data: urls.geojson })
      map.addLayer({
        id: 'potential-fill',
        type: 'fill',
        source: 'potential',
        paint: { 'fill-color': CHERRY, 'fill-opacity': 0, 'fill-opacity-transition': transition(DURATION.fast) },
      })
      map.addLayer({
        id: 'potential-line',
        type: 'line',
        source: 'potential',
        paint: {
          'line-color': CHERRY,
          'line-width': 1.25,
          'line-opacity': 0,
          'line-opacity-transition': transition(DURATION.fast),
        },
      })
      // Realce do polígono sob o cursor: camadas filtradas pelo id, por cima das outras.
      map.addLayer({ id: 'potential-hover-fill', type: 'fill', source: 'potential', filter: NO_FEATURE, paint: { 'fill-color': CHERRY, 'fill-opacity': 0.25 } })
      map.addLayer({ id: 'potential-hover-line', type: 'line', source: 'potential', filter: NO_FEATURE, paint: { 'line-color': CHERRY, 'line-width': 2.5 } })
      // Polígono escolhido no chat: contorno escuro, que fica até outra escolha.
      map.addLayer({ id: 'potential-selected-fill', type: 'fill', source: 'potential', filter: NO_FEATURE, paint: { 'fill-color': CHERRY, 'fill-opacity': 0.35 } })
      map.addLayer({ id: 'potential-selected-line', type: 'line', source: 'potential', filter: NO_FEATURE, paint: { 'line-color': INK, 'line-width': 2.5 } })

      const flown = new Promise<void>((resolve) => {
        if (!fly) return resolve()
        map.once('moveend', () => resolve())
        map.fitBounds(bounds, { padding: 32, duration: FLY_MS, easing: easeOut })
      })
      // As transições esperam a imagem e o GeoJSON: antes disso não há o que mostrar.
      Promise.all([sourceLoaded(map, 'rgb'), sourceLoaded(map, 'potential'), flown]).then(() => {
        if (disposed) return
        revealed.current = true
        applyOverlay(map, latest.current.overlay, latest.current.opacity)
        map.setPaintProperty('potential-fill', 'fill-opacity', FILL_OPACITY)
        map.setPaintProperty('potential-line', 'line-opacity', 1)
        setTimeout(() => latest.current.onRevealed(), reduced ? 0 : DURATION.fast + DURATION.slow)
      })
    })

    let hovered: number | undefined
    const setHover = (id: number | undefined) => {
      if (id === hovered) return
      hovered = id
      const filter = id === undefined ? NO_FEATURE : (['==', ['id'], id] as FilterSpecification)
      map.setFilter('potential-hover-fill', filter)
      map.setFilter('potential-hover-line', filter)
      map.getCanvas().style.cursor = id === undefined ? '' : 'pointer'
    }
    map.on('mousemove', 'potential-fill', (event) => setHover(event.features?.[0]?.id as number | undefined))
    map.on('mouseleave', 'potential-fill', () => setHover(undefined))
    map.on('click', 'potential-fill', (event) => {
      const feature = event.features?.[0]
      if (feature) openPopup(map, popupRef, event.lngLat, feature)
    })

    return () => {
      disposed = true
      map.remove()
      mapRef.current = null
    }
  }, [])

  const { overlay, opacity, focus } = props
  useEffect(() => {
    latest.current = { ...latest.current, overlay, opacity }
    const map = mapRef.current
    if (map?.getLayer('rgb') && revealed.current) applyOverlay(map, overlay, opacity)
  }, [overlay, opacity])

  // "Ver no mapa" (R5.15): enquadra o polígono, destaca e abre o mesmo popup do clique.
  useEffect(() => {
    const map = mapRef.current
    if (!focus || !map?.getLayer('potential-selected-line')) return
    const filter = ['==', ['id'], focus.id] as FilterSpecification
    map.setFilter('potential-selected-fill', filter)
    map.setFilter('potential-selected-line', filter)
    const duration = prefersReducedMotion() ? 0 : FLY_MS
    let cancelled = false
    // Lido do GeoJSON da fonte, não dos tiles: o polígono pode estar fora da tela.
    void map
      .getSource<GeoJSONSource>('potential')
      ?.getData()
      .then((data) => {
        if (cancelled) return
        const feature = (data as PotentialCollection).features.find((f) => f.properties.id === focus.id)
        if (!feature) {
          map.flyTo({ center: focus.centroid, zoom: Math.max(map.getZoom(), 15), duration })
          return
        }
        const box = new LngLatBounds()
        for (const point of outerRings(feature.geometry)) box.extend(point as [number, number])
        map.fitBounds(box, { padding: 80, maxZoom: 16.5, duration, easing: easeOut })
        openPopup(map, popupRef, focus.centroid, feature)
      })
    return () => {
      cancelled = true
    }
  }, [focus])

  return (
    <div
      ref={container}
      className="size-full"
      role="region"
      aria-label="Mapa da análise: imagem, áreas potenciais de café e limite da imagem"
    />
  )
}

const NO_FEATURE: FilterSpecification = ['==', ['id'], -1]

/** Um popup por vez: o do clique e o do chat se substituem. */
function openPopup(map: MapLibre, popupRef: { current: Popup | null }, at: LngLatLike, feature: PopupFeature) {
  popupRef.current?.remove()
  popupRef.current = new Popup({ maxWidth: '16rem', className: 'potential-popup' })
    .setLngLat(at)
    .setDOMContent(popupContent(feature))
    .addTo(map)
}

type PopupFeature = Pick<MapGeoJSONFeature, 'properties'>
type PotentialCollection = {
  features: { properties: { id: number }; geometry: { type: string; coordinates?: unknown } }[]
}

/** Anéis externos de um polígono ou multipolígono; bastam para o enquadramento. */
function outerRings(geometry: { type: string; coordinates?: unknown }): number[][] {
  if (geometry.type === 'Polygon') return (geometry.coordinates as number[][][])[0]
  if (geometry.type === 'MultiPolygon') return (geometry.coordinates as number[][][][]).flatMap((polygon) => polygon[0])
  return []
}

function sourceLoaded(map: MapLibre, id: string) {
  return new Promise<void>((resolve) => {
    const check = () => {
      if (!map.isSourceLoaded(id)) return
      map.off('sourcedata', check)
      resolve()
    }
    map.on('sourcedata', check)
    check()
  })
}

function applyOverlay(map: MapLibre, overlay: Overlay, opacity: number) {
  map.setLayoutProperty('rgb', 'visibility', overlay === 'rgb' ? 'visible' : 'none')
  map.setLayoutProperty('classification', 'visibility', overlay === 'classification' ? 'visible' : 'none')
  map.setPaintProperty(overlay, 'raster-opacity', opacity)
}

function boundary(corners: Corners) {
  return {
    type: 'Feature' as const,
    properties: {},
    geometry: { type: 'Polygon' as const, coordinates: [[...corners, corners[0]]] },
  }
}

/** Conteúdo montado com nós de texto: nada do GeoJSON vira HTML. */
function popupContent(feature: PopupFeature): HTMLElement {
  const { id, area_ha, ndvi_mean } = feature.properties as { id: number; area_ha: number; ndvi_mean: number }
  const root = document.createElement('div')
  const rows: [string, string][] = [
    ['Área', `${formatHa(area_ha)} ha`],
    ['NDVI médio', formatIndex(ndvi_mean)],
  ]
  const title = document.createElement('p')
  title.className = 'font-medium'
  title.textContent = `Área potencial nº ${id}`
  root.append(title)
  const list = document.createElement('dl')
  list.className = 'mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs'
  for (const [label, value] of rows) {
    const term = document.createElement('dt')
    term.className = 'text-muted-foreground'
    term.textContent = label
    const detail = document.createElement('dd')
    detail.className = 'text-right font-mono tabular-nums'
    detail.textContent = value
    list.append(term, detail)
  }
  const note = document.createElement('p')
  note.className = 'mt-2 text-[11px] text-muted-foreground'
  note.textContent = 'Não validada em campo.'
  root.append(list, note)
  return root
}
