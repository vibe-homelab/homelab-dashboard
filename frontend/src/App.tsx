import { useEffect, useCallback } from 'react';
import { Layout } from './components/layout/Layout';
import { Overview } from './components/dashboard/Overview';
import { ServiceCard } from './components/dashboard/ServiceCard';
import { useWebSocket } from './hooks/useWebSocket';
import { useDashboardStore } from './stores/dashboardStore';
import { fetchServices } from './services/api';

function App() {
  const { setServices } = useDashboardStore();
  const services = useDashboardStore((state) => Array.from(state.services.values()));

  // Connect WebSocket
  useWebSocket();

  const loadServices = useCallback(async () => {
    try {
      const data = await fetchServices();
      setServices(data.services);
    } catch (e) {
      console.error('Failed to load services:', e);
    }
  }, [setServices]);

  useEffect(() => {
    loadServices();
  }, [loadServices]);

  return (
    <Layout>
      <Overview />

      <h2 className="text-lg font-semibold text-gray-900 mb-4">Services</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {services.map((service) => (
          <ServiceCard
            key={service.service_id}
            service={service}
            onRefresh={loadServices}
          />
        ))}
      </div>

      {services.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No services configured.</p>
          <p className="text-sm text-gray-400 mt-1">
            Check backend/config.yaml to add services.
          </p>
        </div>
      )}
    </Layout>
  );
}

export default App;
