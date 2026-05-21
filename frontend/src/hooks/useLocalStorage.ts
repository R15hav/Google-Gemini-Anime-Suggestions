import { useState } from 'react'

type Updater<T> = T | ((prev: T) => T)

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [stored, setStored] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item !== null ? (JSON.parse(item) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  const setValue = (value: Updater<T>) => {
    try {
      setStored(prev => {
        const next = typeof value === 'function'
          ? (value as (p: T) => T)(prev)
          : value
        if (next === '' || next === null || next === undefined) {
          window.localStorage.removeItem(key)
        } else {
          window.localStorage.setItem(key, JSON.stringify(next))
        }
        return next
      })
    } catch { /* ignore */ }
  }

  return [stored, setValue] as const
}
