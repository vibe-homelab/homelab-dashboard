import { Clock, X, Loader2 } from 'lucide-react';
import { useDashboardStore } from '../../stores/dashboardStore';
import { cancelRequest } from '../../services/api';
import type { QueueEntry } from '../../types';

const statusStyles: Record<string, { bg: string; text: string }> = {
  pending: { bg: 'bg-gray-100', text: 'text-gray-700' },
  dispatched: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  processing: { bg: 'bg-blue-100', text: 'text-blue-700' },
  completed: { bg: 'bg-green-100', text: 'text-green-700' },
  failed: { bg: 'bg-red-100', text: 'text-red-700' },
  cancelled: { bg: 'bg-gray-100', text: 'text-gray-500' },
  timeout: { bg: 'bg-orange-100', text: 'text-orange-700' },
};

function formatAge(createdAt: string): string {
  const ms = Date.now() - new Date(createdAt).getTime();
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

function QueueEntryRow({ entry }: { entry: QueueEntry }) {
  const style = statusStyles[entry.status] || statusStyles.pending;

  const handleCancel = async () => {
    try {
      await cancelRequest(entry.id);
    } catch (e) {
      console.error('Failed to cancel:', e);
    }
  };

  return (
    <div className="flex items-center gap-3 py-2 px-3 hover:bg-gray-50 rounded">
      {entry.status === 'processing' && (
        <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
      )}
      {entry.status !== 'processing' && (
        <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 truncate">
            {entry.service_id}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}>
            {entry.status}
          </span>
        </div>
        <div className="text-xs text-gray-400">
          {entry.id} &middot; {formatAge(entry.created_at)}
          {entry.gpu_ids.length > 0 && ` \u00b7 GPU ${entry.gpu_ids.join(',')}`}
        </div>
      </div>
      {entry.status === 'pending' && (
        <button
          onClick={handleCancel}
          className="p-1 text-gray-400 hover:text-red-500 rounded"
          title="Cancel"
        >
          <X className="w-4 h-4" />
        </button>
      )}
      {entry.error_message && (
        <span className="text-xs text-red-500 truncate max-w-[120px]" title={entry.error_message}>
          {entry.error_message}
        </span>
      )}
    </div>
  );
}

export function RequestQueue() {
  const queue = useDashboardStore((s) => s.queue);

  if (!queue) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 mb-3">Request Queue</h3>
        <div className="animate-pulse h-20 bg-gray-100 rounded" />
      </div>
    );
  }

  const activeEntries = queue.entries.filter((e) =>
    ['pending', 'dispatched', 'processing'].includes(e.status)
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Request Queue</h3>
        <div className="flex gap-3 text-xs text-gray-500">
          <span>{queue.total_pending} pending</span>
          <span>{queue.total_processing} active</span>
        </div>
      </div>
      {activeEntries.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">Queue is empty</p>
      ) : (
        <div className="divide-y divide-gray-100">
          {activeEntries.map((entry) => (
            <QueueEntryRow key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
