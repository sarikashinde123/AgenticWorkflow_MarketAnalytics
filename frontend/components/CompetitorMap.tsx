'use client'
import { useEffect, useRef, useState } from 'react'
import { usePipelineStore, type MapData } from '@/lib/store'

let leafletLoaded = false

export default function CompetitorMap() {
  const mapData = usePipelineStore(s => s.mapData)
  const mapPreview = usePipelineStore(s => s.mapPreview)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const [ready, setReady] = useState(false)

  const hasCompetitors = mapData && mapData.competitors.length > 0
  const hasPreview = mapPreview != null
  const showMap = hasCompetitors || hasPreview

  // Load Leaflet CSS once
  useEffect(() => {
    if (leafletLoaded) { setReady(true); return }
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    link.onload = () => { leafletLoaded = true; setReady(true) }
    document.head.appendChild(link)
  }, [])

  // Render map
  useEffect(() => {
    if (!ready || !showMap || !mapRef.current) return

    import('leaflet').then(L => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }

      // Decide center and radius
      const centerLat = mapData?.center?.lat ?? mapPreview!.lat
      const centerLng = mapData?.center?.lng ?? mapPreview!.lng
      const radiusKm = mapData?.search_radius_km ?? mapPreview!.radiusKm

      const map = L.map(mapRef.current!, {
        center: [centerLat, centerLng],
        zoom: 13,
        scrollWheelZoom: true,
        attributionControl: true,
      })
      mapInstanceRef.current = map

      // Dark tile layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
      }).addTo(map)

      // Search radius circle
      L.circle([centerLat, centerLng], {
        radius: radiusKm * 1000,
        color: '#f5a524',
        fillColor: '#f5a524',
        fillOpacity: 0.06,
        weight: 1.5,
        dashArray: '6 4',
      }).addTo(map)

      // Business marker (amber)
      const bizIcon = L.divIcon({
        className: '',
        html: `<div style="
          width:32px;height:32px;border-radius:50%;
          background:linear-gradient(135deg,#ffc457,#f5a524);
          border:3px solid #1a1206;
          box-shadow:0 0 12px rgba(245,165,36,0.7);
          display:flex;align-items:center;justify-content:center;
        "><svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1 1 18 0z" stroke="#1a1206" stroke-width="2"/><circle cx="12" cy="10" r="3" stroke="#1a1206" stroke-width="2"/></svg></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -34],
      })
      const bizName = mapData?.business?.name || mapPreview?.label || 'Your Business'
      const bizLocation = mapData?.business?.location || ''
      L.marker([centerLat, centerLng], { icon: bizIcon })
        .addTo(map)
        .bindPopup(`<div style="font-family:sans-serif;font-size:13px;"><strong>${bizName}</strong>${bizLocation ? `<br/><span style="color:#888;">${bizLocation}</span>` : ''}</div>`)

      // Competitor markers
      if (hasCompetitors) {
        console.log('[Map] Adding competitor markers, count:', mapData!.competitors.length)
        const bounds = L.latLngBounds([[centerLat, centerLng]])

        // Seeded random — deterministic per index so positions don't jump on re-render
        function srand(seed: number) {
          const x = Math.sin(seed * 9301 + 49297) * 49297
          return x - Math.floor(x)
        }

        const markerRefs: Record<number, any> = {}
        const location = mapData!.business?.location || ''
        const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

        mapData!.competitors.forEach((comp, i) => {
          const lat = comp.lat ?? (comp as any).latitude
          const lng = comp.lng ?? (comp as any).longitude
          if (lat && lng) {
            markerRefs[i] = addCompetitorMarker(L, map, bounds, comp, lat, lng, i)
          } else {
            // Scatter with varied distance + angle so it doesn't look like a ring
            const angle = srand(i * 7 + 3) * 2 * Math.PI
            const distKm = radiusKm * (0.1 + srand(i * 13 + 51) * 0.7)
            const oLat = (distKm / 111) * Math.cos(angle)
            const oLng = (distKm / (111 * Math.cos(centerLat * Math.PI / 180))) * Math.sin(angle)
            markerRefs[i] = addCompetitorMarker(L, map, bounds, comp, centerLat + oLat, centerLng + oLng, i)
          }
        })

        // Geocode in background — try name + location first, fall back to address
        const geocodeQueue = mapData!.competitors
          .map((comp, i) => ({ comp, index: i }))
          .filter(({ comp }) => !comp.lat && !(comp as any).latitude)

        if (geocodeQueue.length > 0) {
          geocodeQueue.forEach(({ comp, index }, qi) => {
            setTimeout(async () => {
              try {
                const nameQuery = comp.name + (location ? ' ' + location : '')
                const r = await fetch(`${API}/api/geocode?q=${encodeURIComponent(nameQuery)}&limit=1`)
                const data = await r.json()
                if (data?.[0]) {
                  if (markerRefs[index]) map.removeLayer(markerRefs[index])
                  addCompetitorMarker(L, map, bounds, comp, parseFloat(data[0].lat), parseFloat(data[0].lon), index)
                  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
                }
              } catch {
                // Geocoding failed — marker stays at scattered position
              }
            }, qi * 1200)
          })
        }

        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
        }
      }

      setTimeout(() => map.invalidateSize(), 200)
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [ready, mapData, mapPreview])

  if (!showMap) return null

  const radiusLabel = mapData?.search_radius_km ?? mapPreview?.radiusKm ?? 5

  return (
    <div className="panel rounded-xl p-5 animate-in">
      <p className="eyebrow mb-1">Reconnaissance map</p>
      <h2 className="font-display text-xl text-[var(--bone)] mb-3" style={{ letterSpacing: '-0.01em' }}>
        {hasCompetitors ? 'Competitor locations' : 'Search area preview'}
      </h2>
      <div className="rounded-lg overflow-hidden border border-[var(--line-2)]" style={{ height: 380 }}>
        <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      </div>
      <div className="flex items-center gap-4 mt-3 text-[11px] font-mono text-[var(--mute)]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: 'linear-gradient(135deg,#ffc457,#f5a524)', border: '1.5px solid #1a1206' }} />
          Your business
        </span>
        {hasCompetitors && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#37d0a6', border: '1.5px solid #0d2a20' }} />
            Competitors
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full border border-dashed" style={{ borderColor: '#f5a524' }} />
          {radiusLabel} km radius
        </span>
      </div>
    </div>
  )
}

function addCompetitorMarker(L: any, map: any, bounds: any, comp: any, lat: number, lng: number, index: number) {
  const icon = L.divIcon({
    className: '',
    html: `<div style="
      width:26px;height:26px;border-radius:50%;
      background:#37d0a6;
      border:2.5px solid #0d2a20;
      box-shadow:0 0 8px rgba(55,208,166,0.5);
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;color:#0d2a20;
    ">${index + 1}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 26],
    popupAnchor: [0, -28],
  })

  const websiteLink = comp.website
    ? `<br/><a href="${comp.website}" target="_blank" rel="noopener" style="color:#818cf8;font-size:11px;">Visit Website ↗</a>`
    : ''
  const sourceBadge = comp.source
    ? `<br/><span style="font-size:10px;color:#999;">Found on: ${comp.source}</span>`
    : ''

  const marker = L.marker([lat, lng], { icon })
    .addTo(map)
    .bindPopup(`<div style="font-family:sans-serif;font-size:13px;min-width:160px;">
      <strong>${comp.name}</strong>
      ${comp.address ? `<br/><span style="color:#888;font-size:11px;">${comp.address}</span>` : ''}
      ${comp.phone ? `<br/><span style="color:#888;font-size:11px;">📞 ${comp.phone}</span>` : ''}
      ${websiteLink}
      ${sourceBadge}
    </div>`)

  bounds.extend([lat, lng])
  return marker
}
