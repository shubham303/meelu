"use client";

import { useSyncExternalStore } from "react";
import { isAppUserAgent } from "./app-mode";

const subscribe = () => () => {};
const getSnapshot = () => isAppUserAgent(navigator.userAgent);
const getServerSnapshot = () => false;

export function useIsApp(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
