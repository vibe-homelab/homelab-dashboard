import { Activity, Wifi, WifiOff } from 'lucide-react';
import { useDashboardStore } from '../../stores/dashboardStore';

export function Header() {
  const wsConnected = useDashboardStore((state) => state.wsConnected);
  const lastUpdate = useDashboardStore((state) => state.lastUpdate);

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Homelab Dashboard</h1>
            <p className="text-sm text-gray-500">Service Monitoring & Control</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {lastUpdate && (
            <span className="text-sm text-gray-500">
              Last update: {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              wsConnected
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {wsConnected ? (
              <>
                <Wifi className="w-4 h-4" />
                <span>Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
