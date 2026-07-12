'use client'
import { useEffect, useRef, useState } from 'react'

interface Place {
  formatted_address: string
  lat: number | null
  lng: number | null
  place_id: string | null
}

interface NominatimResult {
  display_name: string
  lat: string
  lon: string
  place_id: number
}

interface Props {
  value: string
  onChange: (place: Place) => void
  disabled?: boolean
}

export default function LocationSearch({ value, onChange, disabled }: Props) {
  const [text, setText] = useState(value)
  const [suggestions, setSuggestions] = useState<NominatimResult[]>([])
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

  function fetchSuggestions(query: string) {
    if (query.length < 2) {
      setSuggestions([])
      return
    }
    const url = `${API}/api/geocode?q=${encodeURIComponent(query)}&limit=5`
    fetch(url)
      .then(r => r.json())
      .then((data: NominatimResult[]) => {
        setSuggestions(data)
        setOpen(data.length > 0)
        setActiveIdx(-1)
      })
      .catch(() => setSuggestions([]))
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value
    setText(v)
    onChange({ formatted_address: v, lat: null, lng: null, place_id: null })

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchSuggestions(v), 350)
  }

  function selectSuggestion(s: NominatimResult) {
    setText(s.display_name)
    setSuggestions([])
    setOpen(false)
    onChange({
      formatted_address: s.display_name,
      lat: parseFloat(s.lat),
      lng: parseFloat(s.lon),
      place_id: null,
    })
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx(i => (i < suggestions.length - 1 ? i + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx(i => (i > 0 ? i - 1 : suggestions.length - 1))
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault()
      selectSuggestion(suggestions[activeIdx])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    setText(value)
  }, [value])

  return (
    <div className="relative" ref={wrapperRef}>
      <input
        type="text"
        value={text}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        placeholder="Search a location…"
        disabled={disabled}
        className="field"
        autoComplete="off"
      />
      {text && !disabled && (
        <button
          type="button"
          className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-[rgba(210,190,150,0.15)] transition-colors"
          onClick={() => {
            setText('')
            setSuggestions([])
            setOpen(false)
            onChange({ formatted_address: '', lat: null, lng: null, place_id: null })
          }}
          aria-label="Clear location"
        >
          <svg className="h-4 w-4 text-[var(--mute)] hover:text-[var(--bone)]" viewBox="0 0 24 24" fill="none">
            <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      )}
      {open && suggestions.length > 0 && (
        <ul className="loc-dropdown">
          {suggestions.map((s, i) => (
            <li
              key={s.place_id}
              className={`loc-item ${i === activeIdx ? 'loc-active' : ''}`}
              onMouseDown={() => selectSuggestion(s)}
              onMouseEnter={() => setActiveIdx(i)}
            >
              <svg className="loc-pin" viewBox="0 0 24 24" fill="none">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1 1 18 0z" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
              </svg>
              <span>{s.display_name}</span>
            </li>
          ))}
          <li className="loc-credit">
            <span>Powered by OpenStreetMap</span>
          </li>
        </ul>
      )}
    </div>
  )
}
