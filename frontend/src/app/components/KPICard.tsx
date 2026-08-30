import { ReactNode } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from './ui/utils';

interface KPICardProps {
  title: string;
  value: string;
  trend?: number;
  trendLabel?: string;
  icon?: ReactNode;
  className?: string;
}

export default function KPICard({ title, value, trend, trendLabel, icon, className }: KPICardProps) {
  const isPositive = trend !== undefined && trend >= 0;

  return (
    <div className={cn("bg-white rounded-xl border border-gray-200 p-6", className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-2">{title}</p>
          <p className="text-3xl font-semibold text-gray-900 mb-2">{value}</p>
          {trend !== undefined && (
            <div className="flex items-center gap-1">
              {isPositive ? (
                <TrendingUp className="w-4 h-4 text-green-600" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-600" />
              )}
              <span className={cn(
                "text-sm font-medium",
                isPositive ? "text-green-600" : "text-red-600"
              )}>
                {Math.abs(trend)}%
              </span>
              {trendLabel && (
                <span className="text-sm text-gray-500 ml-1">{trendLabel}</span>
              )}
            </div>
          )}
        </div>
        {icon && (
          <div className="w-12 h-12 rounded-lg bg-red-50 flex items-center justify-center text-[#E10019]">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
