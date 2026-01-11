import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { categories } from '../data/categories';
import McdaFilterPanel from '../components/McdaFilterPanel';
import McdaItemList from '../components/McdaItemList';
import ReverbAcousticGuitarsResultCard from '../components/results/ReverbAcousticGuitarsResultCard';
import InsulinDevicesResultCard from '../components/results/InsulinDevicesResultCard';
import VideoGamesResultCard from '../components/results/VideoGamesResultCard';
import type {
  CriteriaConfig,
  FilterConfig,
  FilterDefinition,
  FiltersState,
  ResultsDisplay
} from '../types';
import { parseSearchTermItemKey } from '../utils/searchTerms';

const DEFAULT_PER_PAGE = 24;
const DEFAULT_EXTERNAL_PER_PAGE = 50;

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

const countActiveSections = (
  config: FilterConfig | null,
  filters: FiltersState,
  sectionOrder: string[]
) => {
  if (!config) return 0;
  const filterMap = new Map((config.filters || []).map((filter) => [filter.key, filter]));
  const keys = sectionOrder.length > 0 ? sectionOrder : buildSectionKeys(config);
  let count = 0;

  keys.forEach((key) => {
    if (parseSearchTermItemKey(key)) {
      count += 1;
      return;
    }
    const filter = filterMap.get(key);
    if (!filter) return;
    const value = filters[key];
    if (filter.type === 'range') {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        const range = value as Record<string, unknown>;
        const min = typeof range.min === 'number' ? range.min : null;
        const max = typeof range.max === 'number' ? range.max : null;
        if (min !== null || max !== null) count += 1;
      }
      return;
    }
    if (filter.type === 'boolean') {
      if (value === true) count += 1;
      return;
    }
    if (Array.isArray(value)) {
      if (value.some((item) => String(item).trim() !== '')) count += 1;
      return;
    }
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      count += 1;
    }
  });

  return count;
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
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);
  const [backendPageInfo, setBackendPageInfo] = useState<PageInfo | null>(null);
  const querySignature = useMemo(
    () => JSON.stringify({ filters, selectedOrder, sectionOrder, perPage }),
    [filters, selectedOrder, sectionOrder, perPage]
  );
  const lastQuerySignature = useRef(querySignature);
  const loadedOptionSources = useRef(new Set<string>());
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();

  useEffect(() => {
    let mounted = true;
    setError('');
    setConfig(null);
    setFilters({});
    setSectionOrder([]);
    setSelectedOrder({});
    setPage(1);
    const defaultPerPage =
      configKey === 'video-games' || configKey === 'reverb-acoustic-guitars'
        ? DEFAULT_EXTERNAL_PER_PAGE
        : DEFAULT_PER_PAGE;
    setPerPage(defaultPerPage);
    loadedOptionSources.current = new Set();
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
    if (!config || !apiBase) {
      return () => {
        mounted = false;
      };
    }
    const filters = config.filters || [];
    const sources = Array.from(
      new Set(
        filters
          .map((filter) => filter.options_source)
          .filter((source): source is string => Boolean(source))
      )
    ).filter((source) => !loadedOptionSources.current.has(source));

    if (sources.length === 0) {
      return () => {
        mounted = false;
      };
    }

    const loadOptions = async () => {
      const optionsBySource = new Map<string, string[]>();
      const notesBySource = new Map<string, string>();
      await Promise.all(
        sources.map(async (source) => {
          const headers: Record<string, string> = { accept: 'application/json' };
          const apiToken = (import.meta.env.VITE_API_TOKEN || '').trim();
          if (apiToken) {
            headers.Authorization = `Bearer ${apiToken}`;
          }
          try {
            const response = await fetch(
              `${apiBase}/api/catalog/options?source=${encodeURIComponent(source)}`,
              { headers }
            );
            if (!response.ok) return;
            const data = await response.json();
            if (Array.isArray(data?.options)) {
              optionsBySource.set(source, data.options);
              if (typeof data?.note === 'string' && data.note.trim()) {
                notesBySource.set(source, data.note.trim());
              }
            }
          } finally {
            loadedOptionSources.current.add(source);
          }
        })
      );
      if (!mounted || optionsBySource.size === 0) return;
      setConfig((prev) => {
        if (!prev) return prev;
        const nextFilters = (prev.filters || []).map((filter) => {
          const source = filter.options_source;
          if (!source || !optionsBySource.has(source)) return filter;
          const note = notesBySource.get(source);
          let helperText = filter.helper_text;
          if (note && !helperText?.includes(note)) {
            helperText = helperText ? `${helperText} ${note}` : note;
          }
          return { ...filter, options: optionsBySource.get(source), helper_text: helperText };
        });
        return { ...prev, filters: nextFilters };
      });
    };

    loadOptions();

    return () => {
      mounted = false;
    };
  }, [config, apiBase]);

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
    const scoringUrl = apiBase ? `${apiBase}/api/listings/search` : '';
    const providerKey = dataSource?.provider_key;
    const useServerScoring = Boolean(apiBase);
    const listingsUrl = scoringUrl;

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
        const minRequired = providerKey === 'reverb_v1' ? 3 : 0;
        const activeSections = countActiveSections(config, filters, sectionOrder);
        if (minRequired && activeSections < minRequired) {
          setItemsError(`Select at least ${minRequired} filter sections to load results.`);
          return;
        }
        const data = await fetchListingsWithFilters(
          listingsUrl,
          'Failed to reach listings API.',
          useServerScoring
            ? {
                config_key: configKey,
                filters,
                selected_order: selectedOrder,
                section_order: sectionOrder,
                page,
                per_page: perPage
              }
            : {
                config_key: configKey,
                filters,
                page,
                per_page: perPage
              }
        );
        const listings = Array.isArray(data?.listings) ? data.listings : [];
        const total = typeof data?.total === 'number' ? data.total : listings.length;
        const perPageValue = typeof data?.per_page === 'number' ? data.per_page : perPage;
        const currentPage = typeof data?.current_page === 'number' ? data.current_page : page;
        const totalPages =
          typeof data?.total_pages === 'number'
            ? data.total_pages
            : Math.max(1, Math.ceil(total / perPageValue));
        if (!mounted) return;
        setItems(listings);
        setBackendPageInfo({
          limit: perPageValue,
          offset: (currentPage - 1) * perPageValue,
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
  }, [configKey, querySignature, page, apiBase, config, perPage]);

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

  const perPageOptions = useMemo(() => {
    const baseOptions = [50, 100, 200];
    const merged = new Set([perPage, ...baseOptions]);
    return Array.from(merged).sort((a, b) => a - b);
  }, [perPage]);

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
      : configKey === 'video-games'
      ? VideoGamesResultCard
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
              perPage={perPage}
              perPageOptions={perPageOptions}
              onPerPageChange={(nextPerPage) => {
                setPerPage(nextPerPage);
                setPage(1);
              }}
              renderItem={renderItem}
              display={display}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
