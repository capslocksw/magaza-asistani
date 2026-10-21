import { BarChart, FunnelChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([BarChart, LineChart, FunnelChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

export const PALETTE = ["#4338ca", "#0f766e", "#c2410c", "#7c3aed", "#0369a1", "#b45309", "#be123c", "#15803d"];

export function EChart({ option, height = 280, label }: { option: EChartsCoreOption; height?: number; label: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.setOption({ color: PALETTE, textStyle: { fontFamily: "Segoe UI, system-ui, sans-serif" }, ...option });
    const resize = () => chart.resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} role="img" aria-label={label} style={{ height }} className="w-full" data-testid="chart" />;
}
