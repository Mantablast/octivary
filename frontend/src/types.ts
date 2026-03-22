export type DataSource = {
  type: string;
  provider_key: string;
};

export type Dataset = {
  label: string;
  data_source: DataSource;
};

export type FilterDefinition = {
  key: string;
  label: string;
  type: 'range' | 'select' | 'date' | 'text' | 'checkboxes' | 'boolean';
  min?: number;
  max?: number;
  options?: string[];
  options_source?: string;
  path?: string;
  placeholder?: string;
  allow_custom?: boolean;
  helper_text?: string;
  search_fields?: string[];
};

export type FilterStateValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number>
  | Record<string, unknown>;

export type FiltersState = Record<string, FilterStateValue>;

export type CriteriaOption = {
  label: string;
  value: string;
  range?: { min?: number; max?: number };
  min?: number;
};

export type CriteriaConfig = {
  key: string;
  label: string;
  type: string;
  path?: string;
  options?: CriteriaOption[];
  allow_custom?: boolean;
  ui?: string;
  placeholder?: string;
  helper_text?: string;
};

export type DisplayMetadata = {
  label: string;
  path?: string;
  paths?: string[];
  format?: 'currency' | 'date';
  currency?: string;
  suffix?: string;
};

export type ResultsDisplay = {
  currency?: string;
  unit?: string;
  title_template?: string;
  subtitle_template?: string;
  image_path?: string;
  empty_image?: string;
  metadata?: DisplayMetadata[];
};

export type FilterSection = {
  title: string;
  filters: string[];
};

export type PriorityDefinition = {
  key: string;
  label: string;
};

export type FilterConfig = {
  config_key: string;
  category_key: string;
  title: string;
  description: string;
  disclaimer?: string;
  datasets: {
    primary: Dataset;
  };
  preset_filters?: Record<string, string | number | boolean>;
  filters?: FilterDefinition[];
  sections?: FilterSection[];
  priorities?: PriorityDefinition[];
  display?: ResultsDisplay;
};

export type FilterConfigItem = {
  key: string;
  label: string;
  description: string;
};

export type Category = {
  key: string;
  label: string;
  description: string;
  filterConfigs: FilterConfigItem[];
};

export type DynamicSearchFilterOption = {
  label: string;
  value: string;
  count?: number | null;
};

export type DynamicSearchFilterSummary = {
  key: string;
  label: string;
  type: string;
  option_count?: number | null;
  options: DynamicSearchFilterOption[];
  min?: number | null;
  max?: number | null;
  path?: string;
  helper_text?: string | null;
};

export type DynamicSearchListingSummary = {
  listing_id: string;
  title: string;
  subtitle?: string | null;
  score: number;
  image_url?: string | null;
  metadata: Array<{ label: string; value: string }>;
  source_url?: string | null;
};

export type DynamicSearchCandidate = {
  config_key: string;
  title: string;
  category_key: string;
  description: string;
  match_score: number;
  evidence_count: number;
  source_type: string;
  local_data_available: boolean;
};

export type DynamicSearchResult = {
  query: string;
  config_key?: string | null;
  config_title?: string | null;
  config_description?: string | null;
  category_key?: string | null;
  evidence_count: number;
  prefill_filters: Record<string, unknown>;
  prefill_selected_order: Record<string, string[]>;
  prefill_section_order: string[];
  generated_config?: FilterConfig | null;
  generated_listings?: Record<string, unknown>[] | null;
  generated_filters: DynamicSearchFilterSummary[];
  listings: DynamicSearchListingSummary[];
  candidates: DynamicSearchCandidate[];
  local_only: boolean;
  note?: string | null;
  open_filter_path?: string | null;
};

export type DynamicSearchJob = {
  job_id: string;
  user_id: string;
  query: string;
  limit: number;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  profile: string;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
  result?: DynamicSearchResult | null;
};
