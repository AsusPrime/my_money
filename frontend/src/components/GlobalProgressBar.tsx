import { useIsFetching, useIsMutating } from '@tanstack/react-query'

export function GlobalProgressBar() {
  const isFetching = useIsFetching()
  const isMutating = useIsMutating()
  const active = isFetching + isMutating > 0

  if (!active) return null

  return (
    <div className="fixed inset-x-0 top-0 z-50 h-0.5 overflow-hidden bg-transparent">
      <div className="h-full w-1/3 animate-[progress-slide_1s_ease-in-out_infinite] bg-accent" />
      <style>{`
        @keyframes progress-slide {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
      `}</style>
    </div>
  )
}
