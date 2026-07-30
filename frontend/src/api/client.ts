import axios, { AxiosInstance } from "axios";
import { env } from "@/env";

const makeClient = (baseURL: string): AxiosInstance => {
  const c = axios.create({
    baseURL,
    timeout: 10_000,
    headers: {
      "Content-Type": "application/json",
      "X-Client": "svacs-dashboard",
    },
  });

  c.interceptors.request.use((cfg) => {
    cfg.headers = cfg.headers ?? {};
    if (!cfg.headers["X-Trace-Id"]) {
      cfg.headers["X-Trace-Id"] = crypto.randomUUID();
    }
    return cfg;
  });

  return c;
};

export const clients = {
  signal: makeClient(env.api.signal),
  perception: makeClient(env.api.perception),
  intelligence: makeClient(env.api.intelligence),
  state: makeClient(env.api.state),
  bucket: makeClient(env.api.bucket),
};
