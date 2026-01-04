export default function Account() {
  return (
    <section className="section">
      <h1>Account</h1>
      <p className="lead">
        Sign in to save searches and sync priorities across devices.
      </p>
      <div className="grid">
        <div className="card">
          <h2>Sign in</h2>
          <label className="field">
            <span>Email</span>
            <input type="email" placeholder="you@example.com" />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" placeholder="••••••••" />
          </label>
          <button className="cta">Continue</button>
        </div>
        <div className="card">
          <h2>Saved searches</h2>
          <p className="muted">Sign in to view your saved priority mixes.</p>
          <div className="placeholder-list">
            <div>Weekend flight deals</div>
            <div>Compact SUVs under $15k</div>
            <div>Studio-ready synths</div>
          </div>
        </div>
      </div>
    </section>
  );
}
