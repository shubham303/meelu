import { CHANNEL_COLOR } from "./types";

export function ChannelDot({ channelKey, size = 18 }: { channelKey: string; size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-[5px] text-[9px] font-semibold uppercase text-white"
      style={{ width: size, height: size, background: CHANNEL_COLOR[channelKey] ?? "#5b6b7f" }}
    >
      {channelKey.slice(0, 2)}
    </span>
  );
}
