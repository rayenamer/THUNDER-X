// A small browser: the page as the executor left it after the last run, with the picked element boxed.
export default function Navigator({ url, result, showHighlight }) {
  return (
    <section className="card navigator">
      <div className="browser-bar">
        <span className="browser-dots">
          <span /><span /><span />
        </span>
        <span className="browser-url mono">{url}</span>
      </div>

      <div className="browser-page">
        {result?.screenshot ? (
          <div className="screenshot">
            <img
              key={result.screenshot.length + (result.xpath ?? "")} /* a new run fades in */
              src={`data:image/jpeg;base64,${result.screenshot}`}
              alt="The page after the step"
            />
            {showHighlight && result.highlight && (
              <Highlight key={`${result.xpath}-${result.highlight.x}-${result.highlight.y}`} result={result} />
            )}
          </div>
        ) : (
          <p className="muted small browser-empty">Run a step to see the page here.</p>
        )}
      </div>
    </section>
  );
}

// The element's box, placed in % of the screenshot so it follows the image's size.
function Highlight({ result }) {
  const box = result.highlight;
  const style = {
    left: `${(box.x / box.viewport_width) * 100}%`,
    top: `${(box.y / box.viewport_height) * 100}%`,
    width: `${(box.width / box.viewport_width) * 100}%`,
    height: `${(box.height / box.viewport_height) * 100}%`,
  };
  return (
    <div className="highlight" style={style}>
      <span className="highlight-label">
        {result.action} · {result.confidence.toFixed(2)}
      </span>
    </div>
  );
}
