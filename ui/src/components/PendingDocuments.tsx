import type { PendingDocument } from "../types";

function hostname(url: string): string {
  try { return new URL(url).hostname; }
  catch { return "official source"; }
}

export function PendingDocuments({ items, importingId, errors, onOpenSource, onUsePdf }: {
  items: PendingDocument[];
  importingId: string | null;
  errors: Record<string, string>;
  onOpenSource: (item: PendingDocument) => void;
  onUsePdf: (item: PendingDocument) => void;
}) {
  return (
    <section className="pending-docs" aria-labelledby="pending-docs-title">
      <div className="pending-intro">
        <h3 id="pending-docs-title">Complete the remaining documents</h3>
        <p>BSE supplied a short notice instead of the full document. Download the PDF, then choose it here—FilingForge will place it in the right folder, convert it to Markdown, and update the index.</p>
      </div>
      <div className="pending-list">
        {items.map((item) => {
          const source = item.issuer_url || item.bse_url;
          const importing = importingId === item.news_id;
          return (
            <article className="pending-card" key={item.news_id}>
              <div className="pending-card-head">
                <div>
                  <div className="pending-type">{item.expected_type}</div>
                  <div className="pending-period">{item.expected_period || item.date}</div>
                </div>
                <span className="pending-badge">Source PDF needed</span>
              </div>
              <div className="pending-headline">{item.headline}</div>
              <div className="pending-reason">{item.reason}</div>
              <div className="pending-host">{item.issuer_url ? "Official source" : "BSE notice"} · {hostname(source)}</div>
              {errors[item.news_id] && <div className="pending-error" role="alert">{errors[item.news_id]}</div>}
              <div className="pending-actions">
                <button type="button" className="secondary" onClick={() => onOpenSource(item)}>
                  {item.issuer_url ? "Get document" : "View BSE notice"}
                </button>
                <button type="button" className="primary pending-use" disabled={importing}
                  onClick={() => onUsePdf(item)}>
                  {importing ? "Adding and converting…" : "Use downloaded PDF"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

