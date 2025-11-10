import Header from '../components/Header';
import Card from '../components/Card';
import { useEffect, useState, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { getStatistics, type CommandLog, type IntentFilter, type DaysFilter } from '../api/api'; // Уявімо, що вони тут є

// --- Кольори для діаграм ---
const PIE_COLORS = {
  'app.open': '#34D399', // green-500
  'app.close': '#F87171', // red-500
  'other': '#60A5FA', // blue-400
};

export default function Analytics() {
  const [logs, setLogs] = useState<CommandLog[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // --- Стан фільтрів ---
  const [intentFilter, setIntentFilter] = useState<IntentFilter>('all');
  const [daysFilter, setDaysFilter] = useState<DaysFilter>(30);

  // --- Ефект для завантаження даних при зміні фільтрів ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // --- РЕАЛЬНИЙ ЗАПИТ ДО API ---
        // Тепер викликаємо функцію, яка має робити fetch
        const data = await getStatistics(intentFilter, daysFilter);
        setLogs(data);
      } catch (err) {
        console.error(err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to load statistics.';
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [intentFilter, daysFilter]); // Перезавантажуємо при зміні фільтрів

  // --- Обчислення даних для графіків ---
  const { pieData, barData } = useMemo(() => {
    const intentCounts: Record<string, number> = {
      'app.open': 0,
      'app.close': 0,
    };
    const appCounts: Record<string, number> = {};

    for (const log of logs) {
      if (log.intent === 'app.open' || log.intent === 'app.close') {
        intentCounts[log.intent]++;
      }

      const app = log.slots.app;
      if (app) {
        appCounts[app] = (appCounts[app] || 0) + 1;
      }
    }

    const pieData = [
      { name: 'Open', value: intentCounts['app.open'] },
      { name: 'Close', value: intentCounts['app.close'] },
    ].filter(d => d.value > 0);

    const barData = Object.entries(appCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10); // Показуємо топ-10

    return { pieData, barData };
  }, [logs]);


  return (
    <div>
      <Header title="Analytics" />

      {/* --- Блок фільтрів --- */}
      <Card className="mb-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div>
            <label htmlFor="intentFilter" className="block text-sm mb-1 opacity-70">
              Intent
            </label>
            <select
              id="intentFilter"
              value={intentFilter}
              onChange={(e) => setIntentFilter(e.target.value as IntentFilter)}
              className="w-full bg-zinc-800 rounded px-3 py-2"
            >
              <option value="all">All Intents</option>
              <option value="app.open">app.open</option>
              <option value="app.close">app.close</option>
            </select>
          </div>
          <div>
            <label htmlFor="daysFilter" className="block text-sm mb-1 opacity-70">
              Period
            </label>
            <select
              id="daysFilter"
              value={daysFilter}
              onChange={(e) => setDaysFilter(Number(e.target.value) as DaysFilter)}
              className="w-full bg-zinc-800 rounded px-3 py-2"
            >
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
              <option value="0">All time</option>
            </select>
          </div>
        </div>
      </Card>

      {error && (
        <Card>
          <div className="text-red-500 font-semibold">{error}</div>
        </Card>
      )}

      {/* --- Блок графіків --- */}
      {!isLoading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <Card>
            <h2 className="text-lg font-semibold mb-4">Intent Distribution</h2>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
                     <Cell key="cell-0" fill={PIE_COLORS['app.open']} />
                     <Cell key="cell-1" fill={PIE_COLORS['app.close']} />
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px]">
                <p className="opacity-70">No data for this period.</p>
              </div>
            )}
          </Card>
          <Card>
            <h2 className="text-lg font-semibold mb-4">Top Apps</h2>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={barData} layout="vertical">
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={80} stroke="#888" />
                  <Tooltip cursor={{ fill: '#374151' }} />
                  <Bar dataKey="count" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
               <div className="flex items-center justify-center h-[300px]">
                <p className="opacity-70">No data for this period.</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* --- Блок з таблицею логів --- */}
      <Card>
        <h2 className="text-lg font-semibold mb-4">Command History</h2>
        {isLoading ? (
          <p className="text-center p-4">Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left">
              <thead>
                <tr className="border-b border-zinc-700">
                  <th className="py-2 px-3">Date</th>
                  <th className="py-2 px-3">Raw Text</th>
                  <th className="py-2 px-3">Intent</th>
                  <th className="py-2 px-3">App</th>
                  <th className="py-2 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {logs.length > 0 ? (
                  logs.map((log) => (
                    <tr key={log.id} className="border-b border-zinc-800 hover:bg-zinc-800">
                      <td className="py-3 px-3 opacity-70">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-3">{log.raw_text}</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          log.intent === 'app.open' ? 'bg-green-600' : 'bg-red-600'
                        }`}>
                          {log.intent}
                        </span>
                      </td>
                      <td className="py-3 px-3">{log.slots.app || 'N/A'}</td>
                      <td className="py-3 px-3">
                        {(log.confidence * 100).toFixed(0)}%
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-4 text-center opacity-70">
                      No logs found for the selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}