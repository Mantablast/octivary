export default function Privacy() {
  return (
    <section className="section">
      <h1>Privacy & Consent</h1>
      <p className="lead">
        Octivary only collects anonymized priority data with your consent. We do not process payments or store affiliate codes client-side.
      </p>
      <div className="card">
        <h2>What we collect</h2>
        <ul className="clean-list">
          <li>Config key, category key, and timestamp</li>
          <li>Aggregated priority weights</li>
          <li>Non-identifying filter selections</li>
        </ul>
        <h2>What we do not collect</h2>
        <ul className="clean-list">
          <li>Names, emails, or personal identifiers</li>
          <li>Raw affiliate or payment data</li>
        </ul>
      </div>
    </section>
  );
}
