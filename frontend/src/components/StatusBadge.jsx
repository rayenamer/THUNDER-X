const LABELS = {
  waiting: "Waiting",
  running: "Running",
  done: "Verified",
  failed: "Failed",
  not_found: "Not found",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${status}`}>
      <span className={`dot dot-${status}`} />
      {LABELS[status]}
    </span>
  );
}
