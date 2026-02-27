import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { App } from "../App";

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  readonly url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(payload: string): void {
    this.sent.push(payload);
  }

  close(): void {
    if (this.onclose) {
      this.onclose({} as CloseEvent);
    }
  }

  emitOpen(): void {
    if (this.onopen) {
      this.onopen({} as Event);
    }
  }

  emitMessage(payload: object): void {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(payload) } as MessageEvent<string>);
    }
  }

  static reset(): void {
    MockWebSocket.instances = [];
  }
}

describe("App", () => {
  const mockFetch = (presets: unknown[] = []) => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      if (url.includes("/api/v1/plugins")) {
        return { ok: true, json: async () => [] } as Response;
      }
      if (url.includes("/api/v1/presets") && method === "GET") {
        return { ok: true, json: async () => presets } as Response;
      }
      if (url.includes("/api/v1/tests/start")) {
        return { ok: true, json: async () => ({ test_id: "test-123" }) } as Response;
      }
      if (url.includes("/api/v1/tests/stop")) {
        return { ok: true, json: async () => ({ status: "stopping" }) } as Response;
      }
      if (url.includes("/api/v1/tests/status/")) {
        return {
          ok: true,
          json: async () => ({
            test_id: "test-123",
            status: "running",
            metrics: {
              request_count: 0,
              success_count: 0,
              failure_count: 0,
              rps: 0,
              avg_response_time: 0,
              active_users_estimate: 0,
            },
          }),
        } as Response;
      }
      return { ok: true, json: async () => ({}) } as Response;
    });

    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  };

  afterEach(() => {
    vi.unstubAllGlobals();
    MockWebSocket.reset();
  });

  it("renders the presets heading", async () => {
    mockFetch();
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "Presets", level: 1 })
    ).toBeInTheDocument();
    await screen.findByText(/no presets yet/i);
  });

  it("renders presets returned from the API", async () => {
    mockFetch([
      {
        id: "preset-1",
        name: "Smoke test",
        config: { test_type: "linear", user_count: 1 },
      },
    ]);

    render(<App />);

    expect(await screen.findByText("Smoke test")).toBeInTheDocument();
  });

  it("loads a preset into the editor when clicking its card", async () => {
    mockFetch([
      {
        id: "preset-1",
        name: "Smoke test",
        config: {
          test_type: "linear",
          duration_seconds: 60,
          spawn_rate: 5,
          user_count: 3,
          num_requests: null,
          target_rps: null,
          distribution: null,
        },
      },
    ]);

    render(<App />);

    fireEvent.click(await screen.findByText("Smoke test"));

    expect(screen.getByLabelText("Preset name")).toHaveValue("Smoke test");
    expect(screen.getByLabelText("Users")).toHaveValue(3);
  });

  it("launches a test and subscribes to websocket metrics", async () => {
    mockFetch();
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Launch test" }));

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    expect(socket.url).toContain("/api/v1/ws/results");
    await act(async () => {
      socket.emitOpen();
    });

    await waitFor(() => {
      expect(socket.sent).toContain(JSON.stringify({ type: "subscribe", test_id: "test-123" }));
    });

    expect(screen.getByText(/tracking test/i)).toBeInTheDocument();
  });

  it("updates KPI cards from websocket metrics and shows terminal status", async () => {
    mockFetch();
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Launch test" }));

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });
    const socket = MockWebSocket.instances[0];
    await act(async () => {
      socket.emitOpen();
    });
    await screen.findByText(/tracking test/i);
    await act(async () => {
      socket.emitMessage({
        type: "metrics",
        test_id: "test-123",
        timestamp: "2026-02-24T18:00:01Z",
        status: "running",
        data: {
          requests_sent: 120,
          responses_received: 118,
          errors: 2,
          rps: 9.8,
          avg_latency_ms: 143.2,
          active_users_estimate: 4,
          configured_users: 10,
        },
      });
    });

    const requestsCard = screen.getByRole("heading", { name: "Requests sent" }).closest(".kpi-card");
    expect(requestsCard).not.toBeNull();
    await waitFor(() => {
      expect(within(requestsCard as HTMLElement).getByText("120")).toBeInTheDocument();
    });
    expect(screen.getByText("running")).toBeInTheDocument();

    await act(async () => {
      socket.emitMessage({
        type: "metrics",
        test_id: "test-123",
        timestamp: "2026-02-24T18:00:02Z",
        status: "completed",
        data: {
          requests_sent: 120,
          responses_received: 118,
          errors: 2,
          rps: 0,
          avg_latency_ms: 143.2,
          active_users_estimate: 0,
          configured_users: 10,
        },
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/run finished with status/i)).toBeInTheDocument();
    });
  });

  it("falls back to status polling before websocket metrics arrive", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      if (url.includes("/api/v1/plugins")) {
        return { ok: true, json: async () => [] } as Response;
      }
      if (url.includes("/api/v1/presets") && method === "GET") {
        return { ok: true, json: async () => [] } as Response;
      }
      if (url.includes("/api/v1/tests/start")) {
        return { ok: true, json: async () => ({ test_id: "test-123" }) } as Response;
      }
      if (url.includes("/api/v1/tests/status/test-123")) {
        return {
          ok: true,
          json: async () => ({
            test_id: "test-123",
            status: "running",
            metrics: {
              request_count: 7,
              success_count: 6,
              failure_count: 1,
              rps: 3.5,
              avg_response_time: 140.2,
              active_users_estimate: 2,
            },
          }),
        } as Response;
      }
      return { ok: true, json: async () => ({}) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Launch test" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/tests/status/test-123");
    });

    const requestsCard = screen.getByRole("heading", { name: "Requests sent" }).closest(".kpi-card");
    expect(requestsCard).not.toBeNull();
    await waitFor(() => {
      expect(within(requestsCard as HTMLElement).getByText("7")).toBeInTheDocument();
    });
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("sends stop request for active test", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Launch test" }));

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });
    await act(async () => {
      MockWebSocket.instances[0].emitOpen();
    });

    fireEvent.click(await screen.findByRole("button", { name: "Stop test" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/tests/stop",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ test_id: "test-123" }),
        })
      );
    });
  });
});
