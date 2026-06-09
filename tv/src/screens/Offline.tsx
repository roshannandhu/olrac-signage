export default function Offline({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="scr scr-off">
      <div className="off-ico">📡</div>
      <div className="off-t">No internet connection</div>
      <div className="off-s">Playing cached content · Last sync 2 hours ago</div>
      <button className="retry-b" onClick={onRetry}>↺ Retry connection</button>
    </div>
  )
}
