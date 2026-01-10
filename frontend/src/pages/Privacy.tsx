export default function Privacy() {
  return (
    <section className="section">
      <h1>Privacy Policy</h1>
      <p className="lead">
        Octivary is built to help you compare products without collecting personal or sensitive health data.
      </p>
      <div className="card">
        <h2>What we collect</h2>
        <p>
          In V1, Octivary does not collect personal information or health data. If you opt in to analytics in the
          future, we may collect anonymous, aggregated interaction data to understand how filters are used.
        </p>

        <h2>What we do not collect</h2>
        <ul className="clean-list">
          <li>Names, email addresses, or account logins</li>
          <li>Medical records, glucose values, or diagnostic information</li>
          <li>Payment details or affiliate tracking data</li>
        </ul>

        <h2>Anonymous interaction data (future)</h2>
        <p>
          We may add anonymized behavior analytics in a later version to improve the product. If we do, we will update
          this policy and provide clear notice. This is not enabled in V1.
        </p>

        <h2>Use of aggregated data</h2>
        <p>
          In the future, we may share or sell aggregated, anonymous insights about how people use filters. This data
          would not identify individuals and would exclude personal or health information.
        </p>

        <h2>Cookies</h2>
        <p>
          Octivary may use minimal cookies or local storage for basic functionality (such as interface preferences).
          We do not use cookies for advertising in V1.
        </p>

        <h2>Your choices</h2>
        <p>
          If optional analytics are introduced later, you will be able to opt in or out. We will make those controls
          easy to find.
        </p>

        <h2>Contact</h2>
        <p>If you have questions, please contact us through the site’s contact link.</p>

        <p className="muted">Last updated: January 10, 2026</p>
      </div>
    </section>
  );
}
