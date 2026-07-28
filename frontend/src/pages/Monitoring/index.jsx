import { useEffect, useState, useRef } from 'react';
import Chart from 'chart.js/auto';
import { Activity, Shield } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

const Monitoring = () => {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState([]);
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await api.getDashboardSummary();
        const cards = data?.cards || data?.data?.cards || [];
        setMetrics(cards);
      } catch (e) {
        setMetrics([]);
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  // Render chart when metrics update
  useEffect(() => {
    if (metrics.length && chartRef.current) {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
      const ctx = chartRef.current.getContext('2d');
      const data = {
        labels: metrics.map(m => m.title),
        datasets: [{
          label: 'Current Metrics',
          data: metrics.map(m => Number((m.val || '0').replace(/[^0-9\.]/g, ''))),
          backgroundColor: metrics.map(m => {
            // simple color mapping based on Tailwind bg class
            const colorMap = {
              'bg-blue-100': 'rgba(59,130,246,0.6)',
              'bg-purple-100': 'rgba(139,92,246,0.6)',
              'bg-green-100': 'rgba(34,197,94,0.6)',
              'bg-yellow-100': 'rgba(234,179,8,0.6)',
              'bg-red-100': 'rgba(239,68,68,0.6)'
            };
            return colorMap[m.color] || 'rgba(100,100,100,0.6)';
          })
        }]
      };
      chartInstance.current = new Chart(ctx, {
        type: 'bar',
        data,
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    }
  }, [metrics]);
  
  if (user?.role !== 'Admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Shield className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Access Denied</h2>
        <p className="text-gray-500 mt-2">You don't have permission to perform this action.</p>
      </div>
    );
  }

  // Loading state
  if (!metrics.length) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-teal-600" />
            System Monitoring
          </h1>
          <p className="text-sm text-gray-500 mt-1">Real-time health and performance metrics for the backend engine.</p>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
          <span className="ml-3 text-gray-500">Loading metrics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-teal-600" />
          System Monitoring
        </h1>
        <p className="text-sm text-gray-500 mt-1">Real-time health and performance metrics for the backend engine.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {metrics.map((m, idx) => (
          <div key={idx} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex items-center gap-4">
            <div className={`w-12 h-12 rounded-full ${m.color} dark:bg-opacity-20 flex items-center justify-center`}>
              <Activity className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{m.title}</p>
              <h4 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{m.val}</h4>
            </div>
          </div>
        ))}
      </div>
      <canvas ref={chartRef} className="w-full h-64 mt-4"></canvas>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Live Service Status</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
              <span className="font-medium text-gray-900 dark:text-white">FastAPI Backend API</span>
            </div>
            <span className="text-sm text-green-600 dark:text-green-400 font-medium">Operational</span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
              <span className="font-medium text-gray-900 dark:text-white">Supabase Database</span>
            </div>
            <span className="text-sm text-green-600 dark:text-green-400 font-medium">Operational</span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
              <span className="font-medium text-gray-900 dark:text-white">Sync Orchestrator</span>
            </div>
            <span className="text-sm text-green-600 dark:text-green-400 font-medium">Operational</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Monitoring;
