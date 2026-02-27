import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Parameter = {
  type: "int" | "float" | "str" | "bool";
  default: unknown;
  description: string;
  required: boolean;
};

type DistributionMetadata = {
  name: string;
  version?: string;
  description?: string;
  parameters: Record<string, Parameter>;
};

type DistributionConfig = {
  name: string;
  config: Record<string, unknown>;
};

type RunConfig = {
  test_type: string;
  duration_seconds?: number | null;
  spawn_rate: number;
  user_count: number;
  num_requests?: number | null;
  target_rps?: number | null;
  distribution?: DistributionConfig | null;
};

type Preset = {
  id: string;
  name: string;
  config: RunConfig;
};

type DraftPreset = {
  id?: string;
  name: string;
  config: RunConfig;
};

type RunStatus =
  | "idle"
  | "pending"
  | "starting"
  | "running"
  | "stopping"
  | "stopped"
  | "completed"
  | "failed";

type WsConnectionStatus = "disconnected" | "connecting" | "connected";

type LiveMetrics = {
  requests_sent: number;
  responses_received: number;
  errors: number;
  rps: number;
  avg_latency_ms: number;
  active_users_estimate: number;
  configured_users: number;
};

type MetricsMessage = {
  type: "metrics";
  test_id: string;
  timestamp: string;
  status: RunStatus;
  data: LiveMetrics;
};

type StatusMetrics = {
  request_count: number;
  success_count: number;
  failure_count: number;
  rps: number;
  avg_response_time: number;
  active_users_estimate?: number;
};

type StatusResponse = {
  test_id: string;
  status: RunStatus;
  metrics: StatusMetrics;
};

type WsMessage =
  | MetricsMessage
  | { type: "ping" }
  | { type: "pong" }
  | { type: "subscribed"; test_id: string }
  | { type: "unsubscribed"; test_id: string }
  | { type: "error"; message?: string };

type HistoryPoint = {
  timestamp: number;
  value: number;
};

const DEFAULT_CONFIG: RunConfig = {
  test_type: "linear",
  duration_seconds: 60,
  spawn_rate: 10,
  user_count: 1,
  num_requests: null,
  target_rps: null,
  distribution: null,
};

const HISTORY_LIMIT = 300;
const TERMINAL_STATUSES: RunStatus[] = ["completed", "failed", "stopped"];

const emptyDraft = (): DraftPreset => ({
  name: "",
  config: { ...DEFAULT_CONFIG },
});

const nextHistory = (current: HistoryPoint[], nextPoint: HistoryPoint): HistoryPoint[] => {
  const updated = [...current, nextPoint];
  if (updated.length <= HISTORY_LIMIT) {
    return updated;
  }
  return updated.slice(updated.length - HISTORY_LIMIT);
};

const isTerminalStatus = (status: RunStatus): boolean => TERMINAL_STATUSES.includes(status);

const formatNumber = (value: number, digits = 0): string =>
  value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

function MiniChart({
  title,
  points,
  color,
  unit,
}: {
  title: string;
  points: HistoryPoint[];
  color: string;
  unit: string;
}) {
  const width = 560;
  const height = 180;
  const padding = 14;

  const latest = points.at(-1)?.value ?? 0;
  const minValue = points.length > 0 ? Math.min(...points.map((point) => point.value)) : 0;
  const maxValue = points.length > 0 ? Math.max(...points.map((point) => point.value)) : 0;

  let path = "";
  let areaPath = "";

  if (points.length > 0) {
    const span = Math.max(1, maxValue - minValue);
    const step = (width - padding * 2) / Math.max(1, points.length - 1);

    const coordinates = points.map((point, index) => {
      const x = padding + index * step;
      const y = height - padding - ((point.value - minValue) / span) * (height - padding * 2);
      return { x, y };
    });

    path = coordinates
      .map((coord, index) => `${index === 0 ? "M" : "L"}${coord.x.toFixed(2)},${coord.y.toFixed(2)}`)
      .join(" ");

    const first = coordinates[0];
    const last = coordinates[coordinates.length - 1];
    areaPath = `${path} L${last.x.toFixed(2)},${(height - padding).toFixed(2)} L${first.x.toFixed(
      2
    )},${(height - padding).toFixed(2)} Z`;
  }

  const gradientId = `gradient-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

  return (
    <article className="chart-card">
      <div className="chart-card__header">
        <h4>{title}</h4>
        <strong>
          {formatNumber(latest, unit === "%" ? 1 : 2)}
          {unit}
        </strong>
      </div>
      {points.length === 0 ? (
        <p className="muted">Waiting for first metrics sample…</p>
      ) : (
        <>
          <svg viewBox={`0 0 ${width} ${height}`} className="chart" role="img" aria-label={`${title} chart`}>
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.35" />
                <stop offset="100%" stopColor={color} stopOpacity="0.02" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width={width} height={height} fill="#fff" />
            <path d={areaPath} fill={`url(#${gradientId})`} />
            <path d={path} fill="none" stroke={color} strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" />
          </svg>
          <div className="chart-card__stats">
            <span>
              min {formatNumber(minValue, 2)}
              {unit}
            </span>
            <span>
              max {formatNumber(maxValue, 2)}
              {unit}
            </span>
          </div>
        </>
      )}
    </article>
  );
}

export function App() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [plugins, setPlugins] = useState<DistributionMetadata[]>([]);
  const [draft, setDraft] = useState<DraftPreset>(emptyDraft);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const [activeTestId, setActiveTestId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus>("idle");
  const [connectionStatus, setConnectionStatus] = useState<WsConnectionStatus>("disconnected");
  const [liveMetrics, setLiveMetrics] = useState<LiveMetrics | null>(null);
  const [requestsHistory, setRequestsHistory] = useState<HistoryPoint[]>([]);
  const [rpsHistory, setRpsHistory] = useState<HistoryPoint[]>([]);
  const [activeUsersHistory, setActiveUsersHistory] = useState<HistoryPoint[]>([]);
  const [isStopping, setIsStopping] = useState<boolean>(false);
  const [activeRunConfiguredUsers, setActiveRunConfiguredUsers] = useState<number>(0);
  const [hasWebSocketSample, setHasWebSocketSample] = useState<boolean>(false);

  const activeTestRef = useRef<string | null>(null);
  const runStatusRef = useRef<RunStatus>("idle");
  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const manualCloseRef = useRef<boolean>(false);

  useEffect(() => {
    activeTestRef.current = activeTestId;
  }, [activeTestId]);

  useEffect(() => {
    runStatusRef.current = runStatus;
  }, [runStatus]);

  const pluginMap = useMemo(() => {
    const map = new Map<string, DistributionMetadata>();
    for (const plugin of plugins) {
      map.set(plugin.name, plugin);
    }
    return map;
  }, [plugins]);

  const nestedPluginOptions = useMemo(() => {
    return plugins
      .map((plugin) => plugin.name)
      .filter((name) => name !== "mix" && name !== "sequence");
  }, [plugins]);

  const successRate = useMemo(() => {
    if (!liveMetrics || liveMetrics.requests_sent <= 0) {
      return 0;
    }
    return (liveMetrics.responses_received / liveMetrics.requests_sent) * 100;
  }, [liveMetrics]);

  const closeSocket = useCallback(() => {
    manualCloseRef.current = true;
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
    setConnectionStatus("disconnected");
  }, []);

  const applyMetricsSnapshot = useCallback(
    (nextStatus: RunStatus, nextMetrics: LiveMetrics, pointTime: number) => {
      setRunStatus(nextStatus);
      setLiveMetrics(nextMetrics);
      setRequestsHistory((current) =>
        nextHistory(current, { timestamp: pointTime, value: nextMetrics.requests_sent })
      );
      setRpsHistory((current) =>
        nextHistory(current, { timestamp: pointTime, value: nextMetrics.rps })
      );
      setActiveUsersHistory((current) =>
        nextHistory(current, {
          timestamp: pointTime,
          value: nextMetrics.active_users_estimate,
        })
      );
    },
    []
  );

  const connectToRunStream = useCallback(
    (testId: string) => {
      if (typeof WebSocket === "undefined") {
        setStatus("WebSocket is unavailable in this browser environment.");
        return;
      }

      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      if (websocketRef.current) {
        manualCloseRef.current = true;
        websocketRef.current.close();
        websocketRef.current = null;
      }
      manualCloseRef.current = false;

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/results`);
      websocketRef.current = socket;
      setConnectionStatus("connecting");

      socket.onopen = () => {
        setConnectionStatus("connected");
        socket.send(JSON.stringify({ type: "subscribe", test_id: testId }));
      };

      socket.onmessage = (event: MessageEvent<string>) => {
        let message: WsMessage;
        try {
          message = JSON.parse(event.data) as WsMessage;
        } catch {
          return;
        }

        if (message.type === "ping") {
          socket.send(JSON.stringify({ type: "ping" }));
          return;
        }

        if (message.type === "error") {
          setStatus(message.message ?? "WebSocket stream error.");
          return;
        }

        if (message.type !== "metrics") {
          return;
        }

        if (message.test_id !== activeTestRef.current) {
          return;
        }

        setHasWebSocketSample(true);

        const pointTime = Number.isNaN(Date.parse(message.timestamp))
          ? Date.now()
          : Date.parse(message.timestamp);

        applyMetricsSnapshot(message.status, message.data, pointTime);
      };

      socket.onclose = () => {
        websocketRef.current = null;
        setConnectionStatus("disconnected");

        if (manualCloseRef.current) {
          return;
        }

        const currentTestId = activeTestRef.current;
        if (!currentTestId || isTerminalStatus(runStatusRef.current)) {
          return;
        }

        reconnectTimerRef.current = window.setTimeout(() => {
          connectToRunStream(currentTestId);
        }, 1000);
      };

      socket.onerror = () => {
        setStatus("Live metrics stream encountered an error.");
      };
    },
    [applyMetricsSnapshot, setStatus]
  );

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [presetsResponse, pluginsResponse] = await Promise.all([
          fetch("/api/v1/presets"),
          fetch("/api/v1/plugins"),
        ]);
        if (!presetsResponse.ok || !pluginsResponse.ok) {
          throw new Error("Failed to load presets or plugins");
        }
        const presetsData = (await presetsResponse.json()) as Preset[];
        const pluginsData = (await pluginsResponse.json()) as DistributionMetadata[];
        if (mounted) {
          setPresets(presetsData);
          setPlugins(pluginsData);
        }
      } catch {
        if (mounted) {
          setStatus("Unable to load presets. Please refresh.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      closeSocket();
    };
  }, [closeSocket]);

  useEffect(() => {
    if (!activeTestId || hasWebSocketSample || isTerminalStatus(runStatus)) {
      return;
    }

    let cancelled = false;

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/v1/tests/status/${activeTestId}`);
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as StatusResponse;
        if (cancelled || payload.test_id !== activeTestId) {
          return;
        }

        const configuredUsers = Math.max(
          0,
          activeRunConfiguredUsers || liveMetrics?.configured_users || 0
        );
        const fallbackMetrics: LiveMetrics = {
          requests_sent: payload.metrics.request_count ?? 0,
          responses_received: payload.metrics.success_count ?? 0,
          errors: payload.metrics.failure_count ?? 0,
          rps: payload.metrics.rps ?? 0,
          avg_latency_ms: payload.metrics.avg_response_time ?? 0,
          active_users_estimate: payload.metrics.active_users_estimate ?? 0,
          configured_users: configuredUsers,
        };
        applyMetricsSnapshot(payload.status, fallbackMetrics, Date.now());
      } catch {
        // Keep fallback polling silent; websocket remains primary channel.
      }
    };

    void pollStatus();
    const intervalId = window.setInterval(() => {
      void pollStatus();
    }, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [
    activeRunConfiguredUsers,
    activeTestId,
    applyMetricsSnapshot,
    hasWebSocketSample,
    liveMetrics?.configured_users,
    runStatus,
  ]);

  const handleSelectPreset = (preset: Preset) => {
    setDraft({
      id: preset.id,
      name: preset.name,
      config: { ...preset.config },
    });
    setStatus("");
  };

  const handleNewPreset = () => {
    setDraft(emptyDraft());
    setStatus("");
  };

  const updateConfig = <K extends keyof RunConfig>(key: K, value: RunConfig[K]) => {
    setDraft((current) => ({
      ...current,
      config: {
        ...current.config,
        [key]: value,
      },
    }));
  };

  const updateDistributionConfig = (value: DistributionConfig | null) => {
    updateConfig("distribution", value);
  };

  const handleSavePreset = async () => {
    setStatus("");
    try {
      const payload = { name: draft.name, config: draft.config };
      const response = await fetch(
        draft.id ? `/api/v1/presets/${draft.id}` : "/api/v1/presets",
        {
          method: draft.id ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail?.detail ?? "Failed to save preset");
      }
      const saved = (await response.json()) as Preset;
      setPresets((current) => {
        const existingIndex = current.findIndex((item) => item.id === saved.id);
        if (existingIndex >= 0) {
          const updated = [...current];
          updated[existingIndex] = saved;
          return updated;
        }
        return [saved, ...current];
      });
      setDraft({ id: saved.id, name: saved.name, config: saved.config });
      setStatus("Preset saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to save preset");
    }
  };

  const handleDeletePreset = async (presetId: string) => {
    setStatus("");
    try {
      const response = await fetch(`/api/v1/presets/${presetId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete preset");
      }
      setPresets((current) => current.filter((item) => item.id !== presetId));
      if (draft.id === presetId) {
        setDraft(emptyDraft());
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to delete preset");
    }
  };

  const handleLaunch = async () => {
    setStatus("");
    setRunStatus("starting");
    setLiveMetrics(null);
    setRequestsHistory([]);
    setRpsHistory([]);
    setActiveUsersHistory([]);
    setHasWebSocketSample(false);
    setActiveRunConfiguredUsers(Math.max(0, Number(draft.config.user_count) || 0));

    try {
      const response = await fetch("/api/v1/tests/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft.config),
      });
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail?.detail ?? "Failed to start test");
      }
      const data = (await response.json()) as { test_id: string };
      setActiveTestId(data.test_id);
      setStatus(`Test starting: ${data.test_id}`);
      connectToRunStream(data.test_id);
    } catch (error) {
      setRunStatus("failed");
      setStatus(error instanceof Error ? error.message : "Failed to start test");
    }
  };

  const handleStop = async () => {
    if (!activeTestId || isStopping) {
      return;
    }

    setStatus("");
    setIsStopping(true);

    try {
      const response = await fetch("/api/v1/tests/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ test_id: activeTestId }),
      });

      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail?.detail ?? "Failed to stop test");
      }

      setRunStatus("stopping");
      setStatus(`Stop requested for test ${activeTestId}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to stop test");
    } finally {
      setIsStopping(false);
    }
  };

  const handleDistributionChange = (name: string) => {
    if (!name) {
      updateDistributionConfig(null);
      return;
    }
    if (name === "mix") {
      updateDistributionConfig({
        name,
        config: {
          target_rps: null,
          components: [
            {
              weight: 1,
              distribution: {
                name: nestedPluginOptions[0] ?? "constant",
                config: {},
              },
            },
          ],
        },
      });
      return;
    }
    if (name === "sequence") {
      updateDistributionConfig({
        name,
        config: {
          post_behavior: "hold_last",
          stages: [
            {
              duration_seconds: 10,
              distribution: {
                name: nestedPluginOptions[0] ?? "constant",
                config: {},
              },
            },
          ],
        },
      });
      return;
    }
    updateDistributionConfig({ name, config: {} });
  };

  const renderParamField = (
    paramName: string,
    param: Parameter,
    value: unknown,
    onChange: (next: unknown) => void
  ) => {
    if (param.type === "bool") {
      return (
        <label key={paramName} className="field field--toggle">
          <span>{paramName}</span>
          <input
            type="checkbox"
            checked={Boolean(value ?? param.default)}
            onChange={(event) => onChange(event.target.checked)}
          />
          <small>{param.description}</small>
        </label>
      );
    }

    const inputType = param.type === "str" ? "text" : "number";
    const displayValue = value ?? param.default ?? "";
    return (
      <label key={paramName} className="field">
        <span>{paramName}</span>
        <input
          type={inputType}
          value={displayValue as string | number}
          onChange={(event) => {
            const raw = event.target.value;
            if (param.type === "str") {
              onChange(raw);
              return;
            }
            const parsed = raw === "" ? null : Number(raw);
            onChange(Number.isNaN(parsed) ? null : parsed);
          }}
        />
        <small>{param.description}</small>
      </label>
    );
  };

  const renderSimpleDistributionForm = (distribution: DistributionConfig) => {
    const metadata = pluginMap.get(distribution.name);
    if (!metadata) {
      return null;
    }
    return (
      <div className="field-grid">
        {Object.entries(metadata.parameters).map(([paramName, param]) =>
          renderParamField(paramName, param, distribution.config[paramName], (next) => {
            updateDistributionConfig({
              ...distribution,
              config: { ...distribution.config, [paramName]: next },
            });
          })
        )}
      </div>
    );
  };

  const renderNestedDistribution = (
    distribution: DistributionConfig,
    onChange: (next: DistributionConfig) => void
  ) => {
    const metadata = pluginMap.get(distribution.name);
    if (!metadata) {
      return null;
    }
    return (
      <div className="nested-config">
        <label className="field">
          <span>Distribution</span>
          <select
            value={distribution.name}
            onChange={(event) => onChange({ name: event.target.value, config: {} })}
          >
            {nestedPluginOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <div className="field-grid">
          {Object.entries(metadata.parameters).map(([paramName, param]) =>
            renderParamField(paramName, param, distribution.config[paramName], (next) => {
              onChange({
                ...distribution,
                config: { ...distribution.config, [paramName]: next },
              });
            })
          )}
        </div>
      </div>
    );
  };

  const renderMixForm = (distribution: DistributionConfig) => {
    const components =
      (distribution.config.components as
        | Array<{ weight: number; distribution: DistributionConfig }>
        | undefined) ?? [];
    const targetRps = distribution.config.target_rps as number | null | undefined;

    return (
      <div className="field-stack">
        <label className="field">
          <span>Default target RPS</span>
          <input
            type="number"
            value={targetRps ?? ""}
            onChange={(event) => {
              const next = event.target.value === "" ? null : Number(event.target.value);
              updateDistributionConfig({
                ...distribution,
                config: { ...distribution.config, target_rps: next },
              });
            }}
          />
          <small>Fallback target RPS for components.</small>
        </label>
        <div className="card card--sub">
          <h3>Components</h3>
          {components.map((component, index) => (
            <div key={index} className="component">
              <label className="field">
                <span>Weight</span>
                <input
                  type="number"
                  value={component.weight}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    const updated = components.map((item, idx) =>
                      idx === index ? { ...item, weight: next } : item
                    );
                    updateDistributionConfig({
                      ...distribution,
                      config: { ...distribution.config, components: updated },
                    });
                  }}
                />
              </label>
              {renderNestedDistribution(component.distribution, (next) => {
                const updated = components.map((item, idx) =>
                  idx === index ? { ...item, distribution: next } : item
                );
                updateDistributionConfig({
                  ...distribution,
                  config: { ...distribution.config, components: updated },
                });
              })}
            </div>
          ))}
          <button
            type="button"
            className="button button--ghost"
            onClick={() => {
              const updated = [
                ...components,
                {
                  weight: 1,
                  distribution: {
                    name: nestedPluginOptions[0] ?? "constant",
                    config: {},
                  },
                },
              ];
              updateDistributionConfig({
                ...distribution,
                config: { ...distribution.config, components: updated },
              });
            }}
          >
            Add component
          </button>
        </div>
      </div>
    );
  };

  const renderSequenceForm = (distribution: DistributionConfig) => {
    const stages =
      (distribution.config.stages as
        | Array<{ duration_seconds: number; distribution: DistributionConfig }>
        | undefined) ?? [];
    const postBehavior =
      (distribution.config.post_behavior as string | undefined) ?? "hold_last";

    return (
      <div className="field-stack">
        <label className="field">
          <span>Post behavior</span>
          <select
            value={postBehavior}
            onChange={(event) => {
              updateDistributionConfig({
                ...distribution,
                config: { ...distribution.config, post_behavior: event.target.value },
              });
            }}
          >
            <option value="hold_last">hold_last</option>
            <option value="zero">zero</option>
            <option value="repeat">repeat</option>
          </select>
          <small>What happens after the final stage completes.</small>
        </label>
        <div className="card card--sub">
          <h3>Stages</h3>
          {stages.map((stage, index) => (
            <div key={index} className="component">
              <label className="field">
                <span>Duration (seconds)</span>
                <input
                  type="number"
                  value={stage.duration_seconds}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    const updated = stages.map((item, idx) =>
                      idx === index ? { ...item, duration_seconds: next } : item
                    );
                    updateDistributionConfig({
                      ...distribution,
                      config: { ...distribution.config, stages: updated },
                    });
                  }}
                />
              </label>
              {renderNestedDistribution(stage.distribution, (next) => {
                const updated = stages.map((item, idx) =>
                  idx === index ? { ...item, distribution: next } : item
                );
                updateDistributionConfig({
                  ...distribution,
                  config: { ...distribution.config, stages: updated },
                });
              })}
            </div>
          ))}
          <button
            type="button"
            className="button button--ghost"
            onClick={() => {
              const updated = [
                ...stages,
                {
                  duration_seconds: 10,
                  distribution: {
                    name: nestedPluginOptions[0] ?? "constant",
                    config: {},
                  },
                },
              ];
              updateDistributionConfig({
                ...distribution,
                config: { ...distribution.config, stages: updated },
              });
            }}
          >
            Add stage
          </button>
        </div>
      </div>
    );
  };

  const distribution = draft.config.distribution ?? null;

  return (
    <div className="app">
      <header className="app__header">
        <p className="app__eyebrow">Primes Load Testing</p>
        <h1>Presets</h1>
        <p className="app__subtitle">Launch tests fast with saved configurations.</p>
      </header>

      <section className="panel panel--wide run-panel">
        <div className="panel__header">
          <h2>Active run</h2>
          <div className="run-panel__actions">
            <span className={`status-pill status-pill--${runStatus}`}>{runStatus}</span>
            <span className="connection-pill">Socket: {connectionStatus}</span>
            <button
              type="button"
              className="button"
              onClick={handleStop}
              disabled={!activeTestId || isStopping || isTerminalStatus(runStatus)}
            >
              {isStopping ? "Stopping…" : "Stop test"}
            </button>
          </div>
        </div>

        {activeTestId ? (
          <p className="run-meta">
            Tracking test <code>{activeTestId}</code>
          </p>
        ) : (
          <p className="muted">Launch a test to start streaming real-time metrics.</p>
        )}

        <div className="kpi-grid">
          <article className="kpi-card">
            <h4>Requests sent</h4>
            <strong>{formatNumber(liveMetrics?.requests_sent ?? 0)}</strong>
          </article>
          <article className="kpi-card">
            <h4>RPS</h4>
            <strong>{formatNumber(liveMetrics?.rps ?? 0, 2)}</strong>
          </article>
          <article className="kpi-card">
            <h4>Active users</h4>
            <strong>{formatNumber(liveMetrics?.active_users_estimate ?? 0)}</strong>
          </article>
          <article className="kpi-card">
            <h4>Errors</h4>
            <strong>{formatNumber(liveMetrics?.errors ?? 0)}</strong>
          </article>
          <article className="kpi-card">
            <h4>Avg latency</h4>
            <strong>{formatNumber(liveMetrics?.avg_latency_ms ?? 0, 2)} ms</strong>
          </article>
          <article className="kpi-card">
            <h4>Success rate</h4>
            <strong>{formatNumber(successRate, 2)}%</strong>
          </article>
        </div>

        <div className="charts-grid">
          <MiniChart title="Requests" points={requestsHistory} color="#f26d4b" unit="" />
          <MiniChart title="RPS" points={rpsHistory} color="#2f7ea1" unit="" />
          <MiniChart title="Active Users" points={activeUsersHistory} color="#2f9f6a" unit="" />
        </div>

        {isTerminalStatus(runStatus) && activeTestId ? (
          <p className="run-summary">Run finished with status <strong>{runStatus}</strong>.</p>
        ) : null}
      </section>

      <section className="app__content">
        <div className="panel">
          <div className="panel__header">
            <h2>Saved presets</h2>
            <button type="button" onClick={handleNewPreset}>
              New preset
            </button>
          </div>
          {loading ? (
            <p>Loading presets…</p>
          ) : presets.length === 0 ? (
            <p>No presets yet. Create your first one.</p>
          ) : (
            <ul className="preset-list">
              {presets.map((preset) => (
                <li
                  key={preset.id}
                  className="preset-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelectPreset(preset)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleSelectPreset(preset);
                    }
                  }}
                >
                  <div>
                    <h3>{preset.name}</h3>
                    <p>
                      {preset.config.test_type} · users {preset.config.user_count}
                    </p>
                  </div>
                  <div className="preset-card__actions">
                    <button
                      type="button"
                      className="button button--ghost"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleSelectPreset(preset);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button--ghost"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDeletePreset(preset.id);
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="panel panel--wide">
          <div className="panel__header">
            <h2>{draft.id ? "Edit preset" : "Create preset"}</h2>
            <button type="button" className="button" onClick={handleLaunch}>
              Launch test
            </button>
          </div>
          {status ? <div className="status">{status}</div> : null}
          <div className="form-grid">
            <label className="field">
              <span>Preset name</span>
              <input
                type="text"
                value={draft.name}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label className="field">
              <span>Test type</span>
              <input
                type="text"
                value={draft.config.test_type}
                onChange={(event) => updateConfig("test_type", event.target.value)}
              />
            </label>
            <label className="field">
              <span>Duration (seconds)</span>
              <input
                type="number"
                value={draft.config.duration_seconds ?? ""}
                onChange={(event) =>
                  updateConfig(
                    "duration_seconds",
                    event.target.value === "" ? null : Number(event.target.value)
                  )
                }
              />
            </label>
            <label className="field">
              <span>Number of requests</span>
              <input
                type="number"
                value={draft.config.num_requests ?? ""}
                onChange={(event) =>
                  updateConfig(
                    "num_requests",
                    event.target.value === "" ? null : Number(event.target.value)
                  )
                }
              />
            </label>
            <label className="field">
              <span>Users</span>
              <input
                type="number"
                value={draft.config.user_count}
                onChange={(event) => updateConfig("user_count", Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span>Spawn rate</span>
              <input
                type="number"
                value={draft.config.spawn_rate}
                onChange={(event) => updateConfig("spawn_rate", Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span>Target RPS</span>
              <input
                type="number"
                value={draft.config.target_rps ?? ""}
                onChange={(event) =>
                  updateConfig(
                    "target_rps",
                    event.target.value === "" ? null : Number(event.target.value)
                  )
                }
              />
            </label>
          </div>
          <div className="distribution">
            <div className="panel__header panel__header--tight">
              <h3>Distribution</h3>
              <label className="field field--toggle">
                <span>Enable</span>
                <input
                  type="checkbox"
                  checked={Boolean(distribution)}
                  onChange={(event) => {
                    if (!event.target.checked) {
                      updateDistributionConfig(null);
                    } else {
                      handleDistributionChange(plugins[0]?.name ?? "constant");
                    }
                  }}
                />
              </label>
            </div>
            {distribution ? (
              <div className="field-stack">
                <label className="field">
                  <span>Distribution type</span>
                  <select
                    value={distribution.name}
                    onChange={(event) => handleDistributionChange(event.target.value)}
                  >
                    {plugins.map((plugin) => (
                      <option key={plugin.name} value={plugin.name}>
                        {plugin.name}
                      </option>
                    ))}
                  </select>
                </label>
                {distribution.name === "mix"
                  ? renderMixForm(distribution)
                  : distribution.name === "sequence"
                    ? renderSequenceForm(distribution)
                    : renderSimpleDistributionForm(distribution)}
              </div>
            ) : (
              <p className="muted">Enable a distribution to configure advanced patterns.</p>
            )}
          </div>
          <div className="panel__footer">
            <button type="button" className="button" onClick={handleSavePreset}>
              Save preset
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
