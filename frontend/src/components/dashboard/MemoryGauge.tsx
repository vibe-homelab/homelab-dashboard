interface MemoryGaugeProps {
  usedPercent: number;
  usedGb?: number;
  totalGb?: number;
}

export function MemoryGauge({ usedPercent, usedGb, totalGb }: MemoryGaugeProps) {
  const getColor = (percent: number) => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Memory</span>
        <span className="text-gray-900 font-medium">
          {usedGb !== undefined && totalGb !== undefined
            ? `${usedGb.toFixed(1)} / ${totalGb.toFixed(1)} GB`
            : `${usedPercent.toFixed(0)}%`}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${getColor(usedPercent)}`}
          style={{ width: `${Math.min(usedPercent, 100)}%` }}
        />
      </div>
    </div>
  );
}
