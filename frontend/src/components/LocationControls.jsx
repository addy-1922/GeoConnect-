export function LocationControls({ sharing, position, status, error, onStart, onStop }) {
  return (
    <div className="loc-controls">
      <div className="loc-title">Location sharing</div>

      {!sharing ? (
        <button className="primary-btn" type="button" onClick={onStart} disabled={status === 'prompt'}>
          {status === 'prompt' ? 'Requesting permission…' : 'Share my location'}
        </button>
      ) : (
        <button className="danger-btn" type="button" onClick={onStop}>
          Stop sharing
        </button>
      )}

      {position ? (
        <div className="loc-detail muted">
          {position.latitude.toFixed(5)}, {position.longitude.toFixed(5)}
          {position.accuracy ? <span> (accuracy {Math.round(position.accuracy)}m)</span> : null}
        </div>
      ) : null}

      {error ? <div className="loc-error">{error}</div> : null}
      {sharing && status === 'error' ? (
        <div className="loc-error">Location updates unavailable while sharing stays on.</div>
      ) : null}
    </div>
  )
}