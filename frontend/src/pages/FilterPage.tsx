import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { categories } from '../data/categories';
import type { FilterConfig, FilterDefinition } from '../types';

const sampleResults: Array<{ id: string; title: string; score: number; price: number }> = [
  { id: '1', title: 'Featured listing', score: 86, price: 420 },
  { id: '2', title: 'Best value pick', score: 79, price: 310 },
  { id: '3', title: 'Premium option', score: 92, price: 680 }
];

export default function FilterPage() {
  const { configKey } = useParams<{ configKey: string }>();
  const [config, setConfig] = useState<FilterConfig | null>(null);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [priorities, setPriorities] = useState<Record<string, number>>({});

  useEffect(() => {
    let mounted = true;
    setError('');
    setConfig(null);
    setFilters({});
    setPriorities({});

    if (!configKey) {
      setError('Missing filter config key.');
      return () => {
        mounted = false;
      };
    }

    fetch(`/config/filters/${configKey}.json`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Missing config for ${configKey}`);
        }
        return response.json() as Promise<FilterConfig>;
      })
      .then((data) => {
        if (!mounted) return;
        setConfig(data);
        const initialFilters: Record<string, string> = {};
        (data.filters || []).forEach((filter) => {
          initialFilters[filter.key] = '';
          if (filter.type === 'range') {
            initialFilters[`${filter.key}_min`] = '';
            initialFilters[`${filter.key}_max`] = '';
          }
        });
        setFilters(initialFilters);
        const initialPriorities: Record<string, number> = {};
        (data.priorities || []).forEach((priority) => {
          initialPriorities[priority.key] = 3;
        });
        setPriorities(initialPriorities);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Failed to load config.');
      });

    return () => {
      mounted = false;
    };
  }, [configKey]);

  const filterDefinitions = useMemo(() => {
    const map = new Map<string, FilterDefinition>();
    (config?.filters || []).forEach((filter) => map.set(filter.key, filter));
    return map;
  }, [config]);

  if (error) {
    return (
      <section className="card">
        <h1>Config missing</h1>
        <p>{error}</p>
      </section>
    );
  }

  if (!config) {
    return (
      <section className="card">
        <h1>Loading filters...</h1>
        <p>Fetching the latest filter config.</p>
      </section>
    );
  }

  const handleFilterChange = (keyName: string, value: string) => {
    setFilters((prev) => ({ ...prev, [keyName]: value }));
  };

  const handlePriorityChange = (keyName: string, value: string) => {
    setPriorities((prev) => ({ ...prev, [keyName]: Number(value) }));
  };

  const renderFilter = (filter?: FilterDefinition) => {
    if (!filter) return null;

    if (filter.type === 'select') {
      const options = filter.options ?? [];
      return (
        <select
          value={filters[filter.key]}
          onChange={(event) => handleFilterChange(filter.key, event.target.value)}
        >
          <option value="">Any</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (filter.type === 'range') {
      const min = filter.min ?? 0;
      const max = filter.max ?? 0;
      return (
        <div className="range-row">
          <input
            type="number"
            placeholder={`Min ${min}`}
            value={filters[`${filter.key}_min`] || ''}
            onChange={(event) => handleFilterChange(`${filter.key}_min`, event.target.value)}
          />
          <input
            type="number"
            placeholder={`Max ${max}`}
            value={filters[`${filter.key}_max`] || ''}
            onChange={(event) => handleFilterChange(`${filter.key}_max`, event.target.value)}
          />
        </div>
      );
    }

    if (filter.type === 'date') {
      return (
        <input
          type="date"
          value={filters[filter.key]}
          onChange={(event) => handleFilterChange(filter.key, event.target.value)}
        />
      );
    }

    return (
      <input
        type="text"
        value={filters[filter.key]}
        onChange={(event) => handleFilterChange(filter.key, event.target.value)}
      />
    );
  };

  const category = categories.find((entry) => entry.key === config.category_key);
  const categoryLabel = category?.label ?? config.category_key;
  const sections = config.sections || [];
  const prioritiesList = config.priorities || [];
  const currency = config.display?.currency ?? 'USD';

  return (
    <section className="filter-page">
      <div className="filter-header">
        <div>
          <p className="eyebrow">{categoryLabel}</p>
          <h1>{config.title}</h1>
          <p className="lead">{config.description}</p>
        </div>
        <div className="filter-meta">
          <div>
            <span>Config key</span>
            <strong>{config.config_key}</strong>
          </div>
          <div>
            <span>Provider</span>
            <strong>{config.datasets?.primary?.data_source?.provider_key}</strong>
          </div>
          <button className="cta">Save this search</button>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h2>Filters</h2>
          <div className="filter-sections">
            {sections.map((section) => (
              <div key={section.title} className="filter-section">
                <h3>{section.title}</h3>
                {section.filters.map((filterKey) => {
                  const filter = filterDefinitions.get(filterKey);
                  return (
                    <label key={filterKey} className="filter-row">
                      <span>{filter?.label}</span>
                      {renderFilter(filter)}
                    </label>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Priorities</h2>
          <p className="muted">Drag weights to tune the MCDA ranking.</p>
          <div className="priority-list">
            {prioritiesList.map((priority) => {
              const weight = priorities[priority.key] ?? 3;
              return (
                <div key={priority.key} className="priority-row">
                  <div>
                    <strong>{priority.label}</strong>
                    <span className="muted">Weight {weight}</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={weight}
                    onChange={(event) => handlePriorityChange(priority.key, event.target.value)}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Results preview</h2>
        <div className="results-grid">
          {sampleResults.map((result) => (
            <div key={result.id} className="result-card">
              <div>
                <strong>{result.title}</strong>
                <p className="muted">Score {result.score}</p>
              </div>
              <div className="price">
                {currency} {result.price}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
