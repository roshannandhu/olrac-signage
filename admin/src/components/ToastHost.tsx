import { useStore } from '../store'

export default function ToastHost() {
  const toasts = useStore((s) => s.toasts)
  return (
    <div className="tc">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type}`}>
          <div className="td" />
          {t.msg}
        </div>
      ))}
    </div>
  )
}
