import { ISSUES_URL } from "../config";
export function ErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-view">
      <div className="msg">{message}</div>
      <button className="primary" onClick={onRetry}>Retry</button>
      <a className="link" href={ISSUES_URL} target="_blank" rel="noreferrer">report this ↗</a>
    </div>
  );
}
