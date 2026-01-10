import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { categories } from '../data/categories';
import McdaFilterPanel from '../components/McdaFilterPanel';
import McdaItemList from '../components/McdaItemList';
import ReverbAcousticGuitarsResultCard from '../components/results/ReverbAcousticGuitarsResultCard';
import InsulinDevicesResultCard from '../components/results/InsulinDevicesResultCard';
import type {
  CriteriaConfig,
  FilterConfig,
  FilterDefinition,
  FiltersState,
  ResultsDisplay
} from '../types';
import { parseSearchTermItemKey } from '../utils/searchTerms';

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
  const filters = config.filters || [];
  const filterKeys = new Set(filters.map((filter) => filter.key));
  const sectionKeys =
    config.sections?.flatMap((section) => section.filters).filter((key) => filterKeys.has(key)) ?? [];
  return sectionKeys.length > 0 ? sectionKeys : filters.map((filter) => filter.key);
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
    placeholder: filter.placeholder,
    helper_text: filter.helper_text
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
  const querySignature = useMemo(
    () => JSON.stringify({ filters, selectedOrder, sectionOrder }),
    [filters, selectedOrder, sectionOrder]
  );
  const lastQuerySignature = useRef(querySignature);
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();

  useEffect(() => {
    let mounted = true;
    setError('');
    setConfig(null);
    setFilters({});
    setSectionOrder([]);
    setSelectedOrder({});
    setPage(1);
    setBackendPageInfo(null);

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

    if (!config) {
      return () => {
        mounted = false;
      };
    }

    const dataSource = config?.datasets?.primary?.data_source;
    const backendUrl = apiBase ? `${apiBase}/api/reverb/listings` : '';
    const scoringUrl = apiBase ? `${apiBase}/api/listings/search` : '';
    const useServerScoring = Boolean(apiBase) && dataSource?.type === 'local_json';

    if (lastQuerySignature.current !== querySignature && page !== 1) {
      lastQuerySignature.current = querySignature;
      setPage(1);
      return () => {
        mounted = false;
      };
    }

    lastQuerySignature.current = querySignature;
    setItemsError('');
    setIsLoadingItems(false);
    setItems([]);
    setBackendPageInfo(null);

    const fetchListingsWithFilters = async (url: string, errorLabel: string, payload: Record<string, unknown>) => {
      const headers: Record<string, string> = {
        accept: 'application/json',
        'content-type': 'application/json'
      };
      const apiToken = (import.meta.env.VITE_API_TOKEN || '').trim();
      if (apiToken) {
        headers.Authorization = `Bearer ${apiToken}`;
      }
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(errorLabel);
      }
      return response.json();
    };

    const loadListings = async () => {
      setIsLoadingItems(true);
      try {
        if (!apiBase) {
          setItemsError('API base is not configured. Set VITE_API_BASE to use MCDA filters.');
          return;
        }
        const data = await fetchListingsWithFilters(
          useServerScoring ? scoringUrl : backendUrl,
          'Failed to reach listings API.',
          useServerScoring
            ? {
                config_key: configKey,
                filters,
                selected_order: selectedOrder,
                section_order: sectionOrder,
                page,
                per_page: PER_PAGE
              }
            : {
                config_key: configKey,
                filters,
                page,
                per_page: PER_PAGE
              }
        );
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
        return;
      } catch (err) {
        if (!mounted) return;
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
  }, [configKey, querySignature, page, apiBase, config]);

  const sectionKeys = useMemo(() => (config ? buildSectionKeys(config) : []), [config]);

  const criteriaSections = useMemo(() => {
    if (!config) return [];
    const filters = config.filters || [];
    const filterMap = new Map(filters.map((filter) => [filter.key, filter]));
    const baseOrderedKeys = sectionOrder.length > 0 ? sectionOrder : sectionKeys;
    return baseOrderedKeys
      .map((key) => {
        const termItem = parseSearchTermItemKey(key);
        if (termItem) {
          const baseFilter = filterMap.get(termItem.baseKey);
          if (!baseFilter) return null;
          const baseConfig = toCriteriaConfig(baseFilter);
          const termLabel = termItem.baseKey === 'additional_notes' ? 'Text' : baseConfig.label;
          return {
            ...baseConfig,
            key,
            label: `${termLabel} - ${termItem.term}`,
            type: 'search_terms',
            ui: 'search_term_item'
          };
        }
        const filter = filterMap.get(key);
        if (!filter) return null;
        return toCriteriaConfig(filter);
      })
      .filter((section): section is CriteriaConfig => Boolean(section));
  }, [config, sectionKeys, sectionOrder]);

  const visibleItems = items;

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
  const disclaimer = (config.disclaimer || '').trim();
  const pageInfo = backendPageInfo ?? undefined;
  const totalCount = backendPageInfo?.total ?? items.length;
  const renderItem =
    configKey === 'reverb-acoustic-guitars'
      ? ReverbAcousticGuitarsResultCard
      : configKey === 'insulin-devices'
      ? InsulinDevicesResultCard
      : undefined;

  return (
    <section className="mcda-shell">
      <div className="mcda-container">
        <header className="mcda-header">
          <div className="mcda-disclaimer">{disclaimer}</div>
          <p className="mcda-eyebrow">{categoryLabel}</p>
          <h1>{config.title}</h1>
          <p className="mcda-lead">{config.description}</p>
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
              isLoading={isLoadingItems}
              error={itemsError ? new Error(itemsError) : null}
              onPageChange={(nextPage) => setPage(nextPage)}
              renderItem={renderItem}
              display={display}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
