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
  type: 'range' | 'select' | 'date' | 'text';
  min?: number;
  max?: number;
  options?: string[];
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
  datasets: {
    primary: Dataset;
  };
  preset_filters?: Record<string, string | number | boolean>;
  filters?: FilterDefinition[];
  sections?: FilterSection[];
  priorities?: PriorityDefinition[];
  display?: {
    currency?: string;
    unit?: string;
  };
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
