import { CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: 'healthy' | 'unhealthy' | 'unknown' | 'running' | 'stopped' | 'starting' | 'error';
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';

  const config = {
    healthy: {
      bg: 'bg-green-100',
      text: 'text-green-700',
      icon: CheckCircle,
      label: 'Healthy',
    },
    running: {
      bg: 'bg-green-100',
      text: 'text-green-700',
      icon: CheckCircle,
      label: 'Running',
    },
    unhealthy: {
      bg: 'bg-red-100',
      text: 'text-red-700',
      icon: XCircle,
      label: 'Unhealthy',
    },
    error: {
      bg: 'bg-red-100',
      text: 'text-red-700',
      icon: XCircle,
      label: 'Error',
    },
    stopped: {
      bg: 'bg-gray-100',
      text: 'text-gray-600',
      icon: AlertCircle,
      label: 'Stopped',
    },
    starting: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-700',
      icon: Loader2,
      label: 'Starting',
    },
    unknown: {
      bg: 'bg-gray-100',
      text: 'text-gray-500',
      icon: AlertCircle,
      label: 'Unknown',
    },
  };

  const { bg, text, icon: Icon, label } = config[status];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${bg} ${text} ${sizeClasses}`}
    >
      <Icon className={`${iconSize} ${status === 'starting' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}
