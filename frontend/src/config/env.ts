type EnvConfig = {
  nodeEnv: string;
  apiBaseUrl: string;
};

export const env: EnvConfig = {
  nodeEnv: process.env.NODE_ENV ?? "development",
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL ?? "",
};
