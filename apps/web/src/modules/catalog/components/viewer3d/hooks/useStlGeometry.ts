import { useEffect, useRef, useState } from "react";
import { BufferAttribute, BufferGeometry } from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

import { stlCache } from "../lib/stlCache";

export type UseStlGeometryArgs = { modelId: string; fileId: string };
export type UseStlGeometryResult = {
  geometry: BufferGeometry | null;
  error: Error | null;
  isLoading: boolean;
};

const WORKER_THRESHOLD_BYTES = 5 * 1024 * 1024;

const loader = new STLLoader();

async function parseStlAsync(buf: ArrayBuffer): Promise<BufferGeometry> {
  if (buf.byteLength < WORKER_THRESHOLD_BYTES) {
    const geom = loader.parse(buf);
    if (geom.getAttribute("normal") === undefined) geom.computeVertexNormals();
    return geom;
  }
  return new Promise((resolve, reject) => {
    const worker = new Worker(
      new URL("../lib/parseStl.worker.ts", import.meta.url),
      { type: "module" },
    );
    const id = Math.floor(Math.random() * 1_000_000_000);
    worker.onmessage = (event: MessageEvent) => {
      const data = event.data as
        | { id: number; ok: true; positions: ArrayBuffer; normals: ArrayBuffer | null }
        | { id: number; ok: false; error: string };
      worker.terminate();
      if (data.id !== id) return;
      if (data.ok === false) {
        reject(new Error(data.error));
        return;
      }
      const geom = new BufferGeometry();
      geom.setAttribute(
        "position",
        new BufferAttribute(new Float32Array(data.positions), 3),
      );
      if (data.normals !== null) {
        geom.setAttribute(
          "normal",
          new BufferAttribute(new Float32Array(data.normals), 3),
        );
      }
      resolve(geom);
    };
    worker.onerror = (e) => {
      worker.terminate();
      reject(new Error(`worker error: ${e.message}`));
    };
    worker.postMessage({ id, buffer: buf }, [buf]);
  });
}

export function useStlGeometry({
  modelId,
  fileId,
}: UseStlGeometryArgs): UseStlGeometryResult {
  // When ids are empty (caller is gating fetch — e.g. waiting on a confirm
  // dialog) skip the network entirely. Returning the same shape keeps the
  // hook drop-in.
  const skip = modelId === "" || fileId === "";
  const url = skip ? "" : `/api/models/${modelId}/files/${fileId}/content`;
  const [geometry, setGeometry] = useState<BufferGeometry | null>(() => {
    if (skip) return null;
    const cached = stlCache.peek(url);
    return cached ?? null;
  });
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(
    !skip && geometry === null,
  );
  const subscribed = useRef<string | null>(null);

  useEffect(() => {
    if (skip) {
      setIsLoading(false);
      setGeometry(null);
      return;
    }
    let cancelled = false;
    setError(null);

    const cached = stlCache.acquire(url);
    if (cached !== undefined) {
      subscribed.current = url;
      setGeometry(cached);
      setIsLoading(false);
      return () => {
        if (subscribed.current !== null) {
          stlCache.release(subscribed.current);
          subscribed.current = null;
        }
      };
    }

    setIsLoading(true);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.arrayBuffer();
      })
      .then((buf) => parseStlAsync(buf))
      .then((geom) => {
        if (cancelled) return;
        stlCache.put(url, geom);
        const handle = stlCache.acquire(url);
        subscribed.current = url;
        setGeometry(handle ?? geom);
        setIsLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
      if (subscribed.current !== null) {
        stlCache.release(subscribed.current);
        subscribed.current = null;
      }
    };
  }, [url, skip]);

  return { geometry, error, isLoading };
}
