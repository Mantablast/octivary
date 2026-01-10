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
  path?: string;
  placeholder?: string;
  allow_custom?: boolean;
  helper_text?: string;
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
