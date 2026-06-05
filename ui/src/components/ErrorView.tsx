export function ErrorView({ message, onRetry, onReport, onBack }: {
  message: string; onRetry: () => void; onReport: () => void; onBack?: () => void;
}) {
  return (
    <div className="error-view">
      {onBack && <button className="back" onClick={onBack}>‹ Back</button>}
      <div className="msg">{message}</div>
      <button className="primary" onClick={onRetry}>Retry</button>
      <button className="link" onClick={onReport}>Report a problem</button>
    </div>
  );
}
