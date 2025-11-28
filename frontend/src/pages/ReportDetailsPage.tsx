import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ReportsAPI } from '../lib/api';

const ReportDetailsPage = () => {
  const { batchId } = useParams();

  const reportQuery = useQuery({
    queryKey: ['report', batchId],
    queryFn: async () => {
      const { data } = await ReportsAPI.getByBatch(batchId!);
      return data;
    },
    enabled: Boolean(batchId),
  });

  if (!batchId) {
    return <p>Не указан batch_id</p>;
  }

  if (reportQuery.isLoading) {
    return <p>Загрузка отчёта…</p>;
  }

  if (!reportQuery.data) {
    return <p>Отчёт не найден</p>;
  }

  const metrics: Record<string, any> = reportQuery.data.metrics || {};
  const missing: Record<string, any> = metrics.missing_values || {};

  return (
    <section className="card" style={{ display: 'grid', gap: 16 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <p style={{ color: 'var(--color-text-muted)', margin: 0 }}>Датасет: {reportQuery.data.batch_id}</p>
          <h2 style={{ margin: 0 }}>Отчёт качества</h2>
        </div>
        <Link to="/reports" style={{ color: 'var(--color-text-muted)' }}>
          ← Назад
        </Link>
      </header>

      <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <InfoCard label="Строк" value={metrics.row_count} />
        <InfoCard label="Домов" value={metrics.house_count} />
        <InfoCard label="Дата с" value={metrics.date_min} />
        <InfoCard label="Дата по" value={metrics.date_max} />
        {metrics.anomaly_count !== undefined && <InfoCard label="Аномалий" value={metrics.anomaly_count} />}
        {metrics.value_stats && (
          <InfoCard
            label="Статистика value"
            value={formatStats(metrics.value_stats)}
          />
        )}
        {metrics.negative_values !== undefined && <InfoCard label="Отрицательных" value={metrics.negative_values} />}
      </div>

      {Object.keys(missing).length > 0 && (
        <div className="card" style={{ background: 'rgba(255,255,255,0.02)', borderStyle: 'dashed' }}>
          <h3 style={{ marginTop: 0 }}>Пропуски по колонкам</h3>
          <ul>
            {Object.entries(missing).map(([col, cnt]) => (
              <li key={col}>
                {col}: {cnt}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};

const InfoCard = ({ label, value }: { label: string; value: any }) => (
  <div className="card" style={{ padding: 12 }}>
    <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 13 }}>{label}</p>
    <h3 style={{ margin: '4px 0 0' }}>{value ?? '—'}</h3>
  </div>
);

const formatStats = (stats: any) => {
  const toNum = (v: any) => {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(2) : v;
  };
  return `min: ${toNum(stats.min)}, max: ${toNum(stats.max)}, mean: ${toNum(stats.mean)}`;
};

export default ReportDetailsPage;
