import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthenticatedImage } from "./AuthenticatedImage";

// The production defect this file pins: `portal_access` has a 10-minute
// max-age and the lightbox stays open longer, so a native `<img>` load for
// `?variant=full` returns 401 with nothing able to refresh it. Measured in
// production 2026-08-02 19:36:41-19:36:55 (ten 401s while the operator
// navigated the viewer) against a refresh session that was still alive at
// 19:26.

const SRC = "/api/models/m1/files/f7/content?variant=full";
const OTHER = "/api/models/m1/files/f8/content?variant=full";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let fetchMock: any;
let createSpy: ReturnType<typeof vi.fn>;
let revokeSpy: ReturnType<typeof vi.fn>;
let objectUrlSeq = 0;

function unauthorized(detail: string): Response {
  return new Response(JSON.stringify({ detail }), { status: 401 });
}
function image(): Response {
  return new Response(new Blob(["binary"], { type: "image/jpeg" }), {
    status: 200,
    headers: { "Content-Type": "image/jpeg" },
  });
}
function img(): HTMLImageElement {
  return screen.getByTestId("authed-image") as HTMLImageElement;
}
function contentCalls(): string[] {
  return fetchMock.mock.calls
    .map((c: unknown[]) => String(c[0]))
    .filter((u: string) => !u.includes("/api/auth/refresh"));
}

beforeEach(() => {
  fetchMock = vi.spyOn(globalThis, "fetch");
  objectUrlSeq = 0;
  createSpy = vi.fn(() => `blob:fake/${++objectUrlSeq}`);
  revokeSpy = vi.fn();
  // jsdom ships neither of these.
  Object.defineProperty(URL, "createObjectURL", { value: createSpy, configurable: true });
  Object.defineProperty(URL, "revokeObjectURL", { value: revokeSpy, configurable: true });
});

afterEach(() => {
  cleanup();
  fetchMock.mockRestore();
});

describe("AuthenticatedImage — happy path is untouched", () => {
  it("renders a plain native <img> and issues no request of its own", () => {
    render(<AuthenticatedImage src={SRC} alt="iso" className="object-contain" />);
    expect(img().getAttribute("src")).toBe(SRC);
    expect(img().getAttribute("alt")).toBe("iso");
    expect(img().className).toBe("object-contain");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(createSpy).not.toHaveBeenCalled();
  });
});

describe("AuthenticatedImage — access-session expiry recovery", () => {
  it("recovers a 401 access_expired load through one refresh and one retry", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 })) // /api/auth/refresh
      .mockResolvedValueOnce(image());

    render(<AuthenticatedImage src={SRC} alt="iso" />);
    fireEvent.error(img());

    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));
    expect(contentCalls()).toEqual([SRC, SRC]);
    expect(createSpy).toHaveBeenCalledTimes(1);
    // No fallback to the anonymous share surface, ever.
    expect(contentCalls().some((u) => u.includes("/api/share"))).toBe(false);
  });

  it("stays on the failed native src when the refresh session is dead", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(unauthorized("refresh_invalid")); // /api/auth/refresh

    render(<AuthenticatedImage src={SRC} alt="iso" />);
    fireEvent.error(img());

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    // Drain the microtask queue before asserting an ABSENCE: `waitFor` above
    // resolves the moment the refresh POST is issued, so without this the
    // assertion would only prove "no retry YET".
    await act(async () => {});
    // The viewer's own inline error state already stands; nothing more happens.
    expect(img().getAttribute("src")).toBe(SRC);
    expect(createSpy).not.toHaveBeenCalled();
    expect(contentCalls()).toEqual([SRC]);
  });

  it("refuses a recovered payload that is not an image", async () => {
    // A misrouted proxy / maintenance page / HTML login redirect arrives as a
    // perfectly valid Blob. Swapping it in would trade a diagnosable URL for an
    // object URL guaranteed to fail decode — and that failure is terminal.
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(
        new Response(new Blob(["<!doctype html>"], { type: "text/html" }), { status: 200 }),
      );

    render(<AuthenticatedImage src={SRC} alt="iso" />);
    fireEvent.error(img());

    await waitFor(() => expect(contentCalls()).toEqual([SRC, SRC]));
    await act(async () => {});
    expect(createSpy).not.toHaveBeenCalled();
    expect(img().getAttribute("src")).toBe(SRC);
  });

  it("attempts recovery at most once per src", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());

    render(<AuthenticatedImage src={SRC} alt="iso" />);
    fireEvent.error(img());
    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));

    // A recovered object URL that itself fails to decode must NOT re-arm the
    // whole chain — that is the retry-storm shape.
    fireEvent.error(img());
    fireEvent.error(img());
    await Promise.resolve();
    expect(contentCalls()).toEqual([SRC, SRC]);
  });

  it("does not re-arm recovery for a src that never failed", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());

    const { rerender } = render(<AuthenticatedImage src={SRC} alt="a" />);
    fireEvent.error(img());
    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));

    rerender(<AuthenticatedImage src={OTHER} alt="b" />);
    expect(img().getAttribute("src")).toBe(OTHER);
    rerender(<AuthenticatedImage src={SRC} alt="a" />);
    // Back on the previously-failed photo: the token is fresh now, so it must
    // load natively again rather than replaying a fetch.
    expect(img().getAttribute("src")).toBe(SRC);
    await Promise.resolve();
    expect(contentCalls()).toEqual([SRC, SRC]);
  });
});

describe("AuthenticatedImage — object URL lifecycle", () => {
  it("revokes the recovered object URL when the photo changes", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());

    const { rerender } = render(<AuthenticatedImage src={SRC} alt="a" />);
    fireEvent.error(img());
    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));

    rerender(<AuthenticatedImage src={OTHER} alt="b" />);
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake/1");
    expect(img().getAttribute("src")).toBe(OTHER);
  });

  it("revokes the recovered object URL on unmount", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());

    const { unmount } = render(<AuthenticatedImage src={SRC} alt="a" />);
    fireEvent.error(img());
    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));

    unmount();
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake/1");
  });

  it("revokes rather than stores an object URL created after unmount", async () => {
    let release!: (r: Response) => void;
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockReturnValueOnce(new Promise<Response>((resolve) => (release = resolve)));

    const { unmount } = render(<AuthenticatedImage src={SRC} alt="a" />);
    fireEvent.error(img());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    unmount();
    release(image());
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
    // This IS the non-vacuous pin on the post-unmount guard: without the
    // `cancelled` check the URL would be handed to `setRecovered` on an
    // unmounted component and the already-run cleanup could never revoke it.
    // (Asserting on a console warning would NOT pin it — React 18 removed the
    // "state update on an unmounted component" warning, so that assertion
    // passes whether or not the guard exists.)
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake/1");
    expect(revokeSpy).toHaveBeenCalledTimes(1);
  });

  it("revokes rather than stores an object URL created after a rapid src change", async () => {
    let release!: (r: Response) => void;
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockReturnValueOnce(new Promise<Response>((resolve) => (release = resolve)));

    const { rerender } = render(<AuthenticatedImage src={SRC} alt="a" />);
    fireEvent.error(img());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    rerender(<AuthenticatedImage src={OTHER} alt="b" />);
    release(image());
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));

    expect(revokeSpy).toHaveBeenCalledWith("blob:fake/1");
    expect(img().getAttribute("src")).toBe(OTHER);
  });

  it("creates and revokes exactly one object URL under StrictMode", async () => {
    // StrictMode double-invokes MOUNT effects. The recovery effect arms on an
    // UPDATE (`armed` false -> true, only after an `error` event), so it is not
    // double-invoked here — this test pins that the whole recovery still
    // completes exactly once inside StrictMode and balances on unmount, rather
    // than pretending to exercise a double-mount it cannot reach.
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());

    const { unmount } = render(
      <StrictMode>
        <AuthenticatedImage src={SRC} alt="a" />
      </StrictMode>,
    );
    fireEvent.error(img());
    await waitFor(() => expect(img().getAttribute("src")).toBe("blob:fake/1"));
    expect(createSpy).toHaveBeenCalledTimes(1);
    expect(revokeSpy).not.toHaveBeenCalled();

    unmount();
    expect(revokeSpy).toHaveBeenCalledTimes(1);
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake/1");
  });
});
