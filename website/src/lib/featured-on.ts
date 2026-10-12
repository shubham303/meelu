export type FeaturedOn = {
  name: string;
  href: string;
  badge?: { src: string; width: number; height: number };
};

export const featuredOn: FeaturedOn[] = [
  {
    name: "Twelve Tools",
    href: "https://twelve.tools",
    badge: { src: "https://twelve.tools/badge0-light.svg", width: 200, height: 54 },
  },
  { name: "ToolPilot", href: "https://www.toolpilot.ai" },
  {
    name: "Toolhunter",
    href: "https://toolhunter.ai/ai-tool/meelu?ref=badge",
    badge: { src: "https://toolhunter.ai/badge/meelu.svg?theme=light", width: 200, height: 50 },
  },
];
