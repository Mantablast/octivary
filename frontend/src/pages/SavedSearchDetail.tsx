import { useParams, Link } from 'react-router-dom';

export default function SavedSearchDetail() {
  const { id } = useParams<{ id: string }>();
  const displayId = id ?? 'unknown';

  return (
    <section className="section">
      <h1>Saved search</h1>
      <p className="lead">Search ID: {displayId}</p>
      <div className="card">
        <h2>Priority snapshot</h2>
        <p className="muted">This is a placeholder saved search detail view.</p>
        <Link className="ghost-link" to="/categories">
          Browse categories
        </Link>
      </div>
    </section>
  );
}
