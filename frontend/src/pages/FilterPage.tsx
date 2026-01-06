import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { categories } from '../data/categories';
import McdaFilterPanel from '../components/McdaFilterPanel';
import McdaItemList from '../components/McdaItemList';
import ReverbAcousticGuitarsResultCard from '../components/results/ReverbAcousticGuitarsResultCard';
import type {
  CriteriaConfig,
  FilterConfig,
  FilterDefinition,
  FiltersState,
  ResultsDisplay
} from '../types';
import { normalize, resolvePath } from '../utils/dataAccess';

const LOCAL_DATASETS: Record<string, string> = {
  'reverb-acoustic-guitars': '/data/reverb-acoustic-guitars.json'
};

const PER_PAGE = 24;

type PageInfo = {
  limit: number;
  offset: number;
  returned: number;
  total: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
};

const buildSectionKeys = (config: FilterConfig) => {
  const filterKeys = new Set((config.filters || []).map((filter) => filter.key));
  const sectionKeys =
    config.sections?.flatMap((section) => section.filters).filter((key) => filterKeys.has(key)) ?? [];
  if (sectionKeys.length > 0) {
    return sectionKeys;
  }
  return (config.filters || []).map((filter) => filter.key);
};

const buildInitialFilters = (filters: FilterDefinition[]) => {
  const initial: FiltersState = {};
  filters.forEach((filter) => {
    if (filter.type === 'checkboxes') {
      initial[filter.key] = [];
    } else if (filter.type === 'boolean') {
      initial[filter.key] = false;
    } else if (filter.type === 'range') {
      initial[filter.key] = { min: null, max: null };
    } else if (filter.type === 'text') {
      initial[filter.key] = [];
    } else {
      initial[filter.key] = null;
    }
  });
  return initial;
};

const toCriteriaConfig = (filter: FilterDefinition): CriteriaConfig => {
  const options = (filter.options || []).map((option) => ({ label: option, value: option }));
  let type = 'scalar';
  let ui: string | undefined;

  if (filter.type === 'checkboxes') {
    type = 'match_any';
  } else if (filter.type === 'boolean') {
    type = 'boolean';
    ui = 'toggle';
  } else if (filter.type === 'range') {
    type = 'range';
    ui = 'range';
  } else if (filter.type === 'select') {
    type = 'dropdown';
    ui = 'dropdown';
  } else if (filter.type === 'text') {
    type = 'search_terms';
    ui = 'search_terms';
  }

  return {
    key: filter.key,
    label: filter.label,
    type,
    path: filter.path,
    options,
    allow_custom: filter.allow_custom,
    ui,
    placeholder: filter.placeholder
  };
};

const buildDisplay = (config: FilterConfig): ResultsDisplay => {
  const base = config.display || {};
  const currency = base.currency || 'USD';
  return {
    ...base,
    title_template: base.title_template || '{title}',
    subtitle_template: base.subtitle_template || '{make} {model}',
    image_path: base.image_path || 'photos[0]._links.large_crop.href',
    empty_image: base.empty_image || '/assets/octonotes.png',
    metadata:
      base.metadata ||
      [
        { label: 'Price', path: 'price.amount', format: 'currency', currency },
        { label: 'Condition', path: 'condition.display_name' },
        { label: 'Year', path: 'year' },
        { label: 'Finish', path: 'finish' },
        { label: 'Shop', path: 'shop_name' }
      ]
  };
};

const stripHtml = (value: string) => value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

const matchesFilter = (item: Record<string, any>, filter: FilterDefinition, filters: FiltersState) => {
  const rawValue = resolvePath(item, filter.path);

  if (filter.type === 'checkboxes') {
    const selected = Array.isArray(filters[filter.key]) ? (filters[filter.key] as string[]) : [];
    if (selected.length === 0) return true;
    const selectedSet = new Set(selected.map((option) => normalize(option)));
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    return values.some((value) => selectedSet.has(normalize(value)));
  }

  if (filter.type === 'boolean') {
    const isEnabled = Boolean(filters[filter.key]);
    if (!isEnabled) return true;
    return Boolean(rawValue);
  }

  if (filter.type === 'range') {
    const range = filters[filter.key];
    if (!range || typeof range !== 'object' || Array.isArray(range)) return true;
    const rangeValue = range as Record<string, unknown>;
    const min = typeof rangeValue.min === 'number' ? rangeValue.min : null;
    const max = typeof rangeValue.max === 'number' ? rangeValue.max : null;
    if (min === null && max === null) return true;
    const numericValue = Number(rawValue);
    if (Number.isNaN(numericValue)) return false;
    if (min !== null && numericValue < min) return false;
    if (max !== null && numericValue > max) return false;
    return true;
  }

  if (filter.type === 'text') {
    const terms = Array.isArray(filters[filter.key]) ? (filters[filter.key] as string[]) : [];
    if (terms.length === 0) return true;
    const haystack = normalize(stripHtml(String(rawValue || '')));
    return terms.some((term) => haystack.includes(normalize(term)));
  }

  if (filter.type === 'select') {
    const selected = filters[filter.key];
    if (!selected) return true;
    return normalize(selected) === normalize(rawValue);
  }

  return true;
};

export default function FilterPage() {
  const { configKey } = useParams<{ configKey: string }>();
  const [config, setConfig] = useState<FilterConfig | null>(null);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<FiltersState>({});
  const [sectionOrder, setSectionOrder] = useState<string[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Record<string, string[]>>({});
  const [items, setItems] = useState<Record<string, any>[]>([]);
  const [itemsError, setItemsError] = useState('');
  const [isLoadingItems, setIsLoadingItems] = useState(false);
  const [page, setPage] = useState(1);
  const [backendPageInfo, setBackendPageInfo] = useState<PageInfo | null>(null);
  const [useLocalFallback, setUseLocalFallback] = useState(false);
  const filtersSignature = useMemo(() => JSON.stringify(filters), [filters]);
  const lastFiltersSignature = useRef(filtersSignature);
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
  const isBackend = Boolean(apiBase) && !useLocalFallback;

  useEffect(() => {
    let mounted = true;
    setError('');
    setConfig(null);
    setFilters({});
    setSectionOrder([]);
    setSelectedOrder({});
    setPage(1);
    setBackendPageInfo(null);
    setUseLocalFallback(false);

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
        const configFilters = data.filters || [];
        setFilters(buildInitialFilters(configFilters));
        setSectionOrder(buildSectionKeys(data));
        setSelectedOrder({});
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Failed to load config.');
      });

    return () => {
      mounted = false;
    };
  }, [configKey]);

  useEffect(() => {
    let mounted = true;

    if (!configKey) return () => {
      mounted = false;
    };

    const dataset = LOCAL_DATASETS[configKey];
    const backendUrl = apiBase ? `${apiBase}/api/reverb/listings` : '';

    if (lastFiltersSignature.current !== filtersSignature && page !== 1) {
      lastFiltersSignature.current = filtersSignature;
      setPage(1);
      return () => {
        mounted = false;
      };
    }

    lastFiltersSignature.current = filtersSignature;
    setItemsError('');
    setIsLoadingItems(false);
    setItems([]);
    setBackendPageInfo(null);

    const fetchListings = async (url: string, errorLabel: string) => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(errorLabel);
      }
      const data = await response.json();
      return Array.isArray(data?.listings) ? data.listings : [];
    };

    const fetchListingsWithFilters = async (url: string, errorLabel: string) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json'
        },
        body: JSON.stringify({
          config_key: configKey,
          filters,
          page,
          per_page: PER_PAGE
        })
      });
      if (!response.ok) {
        throw new Error(errorLabel);
      }
      return response.json();
    };

    const loadListings = async () => {
      setIsLoadingItems(true);
      try {
        if (backendUrl) {
          const data = await fetchListingsWithFilters(backendUrl, 'Failed to reach Reverb API.');
          const listings = Array.isArray(data?.listings) ? data.listings : [];
          const total = typeof data?.total === 'number' ? data.total : listings.length;
          const perPage = typeof data?.per_page === 'number' ? data.per_page : PER_PAGE;
          const currentPage = typeof data?.current_page === 'number' ? data.current_page : page;
          const totalPages =
            typeof data?.total_pages === 'number'
              ? data.total_pages
              : Math.max(1, Math.ceil(total / perPage));
          if (!mounted) return;
          setItems(listings);
          setBackendPageInfo({
            limit: perPage,
            offset: (currentPage - 1) * perPage,
            returned: listings.length,
            total,
            hasNextPage: currentPage < totalPages,
            hasPrevPage: currentPage > 1
          });
          setUseLocalFallback(false);
          return;
        }
        if (dataset) {
          const listings = await fetchListings(dataset, 'Missing sample data.');
          if (!mounted) return;
          setItems(listings);
          setUseLocalFallback(true);
          return;
        }
      } catch (err) {
        if (!mounted) return;
        if (backendUrl && dataset) {
          try {
            const listings = await fetchListings(dataset, 'Missing sample data.');
            if (!mounted) return;
            setItems(listings);
            setUseLocalFallback(true);
            return;
          } catch (fallbackError) {
            setItemsError(
              fallbackError instanceof Error ? fallbackError.message : 'Failed to load listings.'
            );
            return;
          }
        }
        setItemsError(err instanceof Error ? err.message : 'Failed to load listings.');
      } finally {
        if (!mounted) return;
        setIsLoadingItems(false);
      }
    };

    const timer = window.setTimeout(() => {
      loadListings();
    }, 320);

    return () => {
      mounted = false;
      window.clearTimeout(timer);
    };
  }, [configKey, filtersSignature, page, apiBase]);

  const sectionKeys = useMemo(() => (config ? buildSectionKeys(config) : []), [config]);

  const criteriaSections = useMemo(() => {
    if (!config) return [];
    const filterMap = new Map((config.filters || []).map((filter) => [filter.key, filter]));
    return sectionKeys
      .map((key) => {
        const filter = filterMap.get(key);
        if (!filter) return null;
        return toCriteriaConfig(filter);
      })
      .filter((section): section is CriteriaConfig => Boolean(section));
  }, [config, sectionKeys]);

  const filteredItems = useMemo(() => {
    if (!config || !config.filters) return [];
    if (!items.length) return [];
    return items.filter((item) => config.filters!.every((filter) => matchesFilter(item, filter, filters)));
  }, [items, config, filters]);

  const visibleItems = useMemo(() => {
    if (isBackend) return filteredItems;
    const start = (page - 1) * PER_PAGE;
    return filteredItems.slice(start, start + PER_PAGE);
  }, [filteredItems, page, isBackend]);

  const localPageInfo = useMemo<PageInfo | null>(() => {
    if (isBackend) return null;
    const total = filteredItems.length;
    const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
    const safePage = Math.min(page, totalPages);
    return {
      limit: PER_PAGE,
      offset: (safePage - 1) * PER_PAGE,
      returned: visibleItems.length,
      total,
      hasNextPage: safePage < totalPages,
      hasPrevPage: safePage > 1
    };
  }, [filteredItems.length, visibleItems.length, page, isBackend]);

  useEffect(() => {
    if (isBackend) return;
    const totalPages = Math.max(1, Math.ceil(filteredItems.length / PER_PAGE));
    if (page > totalPages) {
      setPage(1);
    }
  }, [filteredItems.length, page, isBackend]);

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

  const category = categories.find((entry) => entry.key === config.category_key);
  const categoryLabel = category?.label ?? config.category_key;
  const display = buildDisplay(config);
  const pageInfo = isBackend ? backendPageInfo : localPageInfo;
  const totalCount = isBackend
    ? backendPageInfo?.total ?? filteredItems.length
    : filteredItems.length;
  const renderItem =
    configKey === 'reverb-acoustic-guitars' ? ReverbAcousticGuitarsResultCard : undefined;

  return (
    <section className="mcda-shell">
      <div className="mcda-container">
        <header className="mcda-header">
          <p className="mcda-eyebrow">{categoryLabel}</p>
          <h1>{config.title}</h1>
          <p className="mcda-lead">{config.description}</p>
          <div className="mcda-meta">
            <div>
              <span>Config key</span>
              <strong>{config.config_key}</strong>
            </div>
            <div>
              <span>Provider</span>
              <strong>{config.datasets?.primary?.data_source?.provider_key}</strong>
            </div>
          </div>
        </header>

        <div className="mcda-main">
          <div className="mcda-layout">
            <McdaFilterPanel
              sections={criteriaSections}
              filters={filters}
              setFilters={setFilters}
              sectionOrder={sectionOrder}
              setSectionOrder={setSectionOrder}
              selectedOrder={selectedOrder}
              setSelectedOrder={setSelectedOrder}
              description={config.description}
            />

            <McdaItemList
              items={visibleItems}
              totalCount={totalCount}
              pageInfo={pageInfo ?? undefined}
              sectionOrder={sectionOrder}
              selectedOrder={selectedOrder}
              isLoading={isLoadingItems}
              error={itemsError ? new Error(itemsError) : null}
              onPageChange={(nextPage) => setPage(nextPage)}
              renderItem={renderItem}
              display={display}
              sections={criteriaSections}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
