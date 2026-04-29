import { useState } from 'react'

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [stored, setStored] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item !== null ? (JSON.parse(item) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  const setValue = (value: T) => {
    try {
      setStored(value)
      if (value === '' || value === null || value === undefined) {
        window.localStorage.removeItem(key)
      } else {
        window.localStorage.setItem(key, JSON.stringify(value))
      }
    } catch { /* ignore */ }
  }

  return [stored, setValue] as const
}
