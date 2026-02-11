import { useEffect, useCallback } from 'react';
import { Layout } from './components/layout/Layout';
import { Overview } from './components/dashboard/Overview';
import { GpuAllocationMap } from './components/dashboard/GpuAllocationMap';
import { RequestQueue } from './components/dashboard/RequestQueue';
import { ServiceCard } from './components/dashboard/ServiceCard';
import { useWebSocket } from './hooks/useWebSocket';
import { useDashboardStore } from './stores/dashboardStore';
import { fetchServices } from './services/api';

function App() {
  const setAllServices = useDashboardStore((s) => s.setAllServices);
  const services = useDashboardStore((s) => s.services);
  const serviceList = Object.values(services);

  useWebSocket();

  const loadServices = useCallback(async () => {
    try {
      const data = await fetchServices();
      // Convert array to record
      const record: Record<string, typeof data.services[0]> = {};
      for (const svc of data.services) {
        record[svc.service_id] = svc;
      }
      setAllServices(record);
    } catch (e) {
      console.error('Failed to load services:', e);
    }
  }, [setAllServices]);

  useEffect(() => {
    loadServices();
  }, [loadServices]);

  return (
    <Layout>
      <Overview />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <GpuAllocationMap />
        <RequestQueue />
      </div>

      <h2 className="text-lg font-semibold text-gray-900 mb-4">Services</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {serviceList.map((service) => (
          <ServiceCard key={service.service_id} service={service} />
        ))}
      </div>

      {serviceList.length === 0 && (
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
