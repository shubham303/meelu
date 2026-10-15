export type Listener<T> = (m: T) => void;

export interface Channel<T> {
  on: (cb: Listener<T>) => () => void;
  emit: (m: T) => void;
}

export function channel<T>(): Channel<T> {
  const listeners = new Set<Listener<T>>();
  return {
    on(cb) {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
    emit(m) {
      for (const l of [...listeners]) l(m);
    },
  };
}

export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

let seq = 0;
export function uid(prefix: string): string {
  seq += 1;
  return `${prefix}_${seq.toString(36)}${Date.now().toString(36).slice(-4)}`;
}
