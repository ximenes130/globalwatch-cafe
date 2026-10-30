import {
  LngLatBounds,
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

type Props = {
  corners: Corners
  urls: ResultUrls
  overlay: Overlay
  opacity: number
}

/**
 * Mapa com a imagem pelos 4 cantos, polígonos da área potencial e limite da imagem (R4.5, R4.7).
 *
 * Criado uma vez por análise (o pai usa `key={id}`): as URLs assinadas mudam a cada consulta
 * da API e não devem recriar o mapa. Camada e opacidade mudam pelo segundo efeito.
 */
export default function MapView(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibre | null>(null)
  const latest = useRef(props)

  useEffect(() => {
    const { corners, urls } = latest.current
    const bounds = corners.reduce((box, corner) => box.extend(corner), new LngLatBounds(corners[0], corners[0]))
    const map = new MapLibre({
      container: container.current!,
      style: BASEMAP,
      bounds,
      fitBoundsOptions: { padding: 32 },
      locale: LOCALE,
      attributionControl: { compact: true, customAttribution: SENTINEL_ATTRIBUTION },
      // No celular o mapa fica no meio da página: um dedo rola a página, dois movem o mapa.
      cooperativeGestures: window.matchMedia('(max-width: 1023px)').matches,
    })
    mapRef.current = map
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')

    map.on('load', () => {
      // Rasters abaixo dos rótulos do basemap; vetores por cima de tudo.
      const firstLabel = map.getStyle().layers.find((layer) => layer.type === 'symbol')?.id
      for (const [id, url] of [['rgb', urls.rgb_png], ['classification', urls.classification_png]] as const) {
        map.addSource(id, { type: 'image', url, coordinates: corners })
        map.addLayer(
          { id, type: 'raster', source: id, paint: { 'raster-fade-duration': 0, 'raster-resampling': 'nearest' } },
          firstLabel,
        )
      }
      applyOverlay(map, latest.current.overlay, latest.current.opacity)

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
        paint: {
          'fill-color': CHERRY,
          'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.4, 0.18],
        },
      })
      map.addLayer({
        id: 'potential-line',
        type: 'line',
        source: 'potential',
        paint: {
          'line-color': CHERRY,
          'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2.5, 1.25],
        },
      })
    })

    let hovered: string | number | undefined
    const setHover = (id: string | number | undefined) => {
      if (hovered !== undefined) map.setFeatureState({ source: 'potential', id: hovered }, { hover: false })
      hovered = id
      if (id !== undefined) map.setFeatureState({ source: 'potential', id }, { hover: true })
      map.getCanvas().style.cursor = id === undefined ? '' : 'pointer'
    }
    map.on('mousemove', 'potential-fill', (event) => setHover(event.features?.[0]?.id))
    map.on('mouseleave', 'potential-fill', () => setHover(undefined))
    map.on('click', 'potential-fill', (event) => {
      const feature = event.features?.[0]
      if (!feature) return
      new Popup({ maxWidth: '16rem', className: 'potential-popup' })
        .setLngLat(event.lngLat)
        .setDOMContent(popupContent(feature))
        .addTo(map)
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  const { overlay, opacity } = props
  useEffect(() => {
    latest.current = { ...latest.current, overlay, opacity }
    const map = mapRef.current
    if (map?.getLayer('rgb')) applyOverlay(map, overlay, opacity)
  }, [overlay, opacity])

  return (
    <div
      ref={container}
      className="size-full"
      role="region"
      aria-label="Mapa da análise: imagem, áreas potenciais de café e limite da imagem"
    />
  )
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
function popupContent(feature: MapGeoJSONFeature): HTMLElement {
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
