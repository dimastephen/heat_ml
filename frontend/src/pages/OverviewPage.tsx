import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { DatasetAPI, ForecastAPI, ReportsAPI } from '../lib/api';

const OverviewPage = () => {
  const navigate = useNavigate();

  const datasetsQuery = useQuery({
    queryKey: ['datasets', 'overview'],
    queryFn: async () => {
      const { data } = await DatasetAPI.list({ limit: 20 });
      return data.items ?? [];
    },
  });

  const forecastsQuery = useQuery({
    queryKey: ['forecasts', 'overview'],
    queryFn: async () => {
      const { data } = await ForecastAPI.list({ limit: 20 });
      return data.items ?? [];
    },
  });

  const reportsQuery = useQuery({
    queryKey: ['reports', 'overview'],
    queryFn: async () => {
      const { data } = await ReportsAPI.list();
      return data.items ?? [];
    },
  });

  const stats = [
    { label: 'Датасеты', value: datasetsQuery.data?.length ?? 0 },
    { label: 'Прогнозы', value: forecastsQuery.data?.length ?? 0 },
    { label: 'Отчёты', value: reportsQuery.data?.length ?? 0 },
  ];

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section className="card" style={{ display: 'grid', gap: 12 }}>
        <p style={{ color: 'var(--color-text-muted)', letterSpacing: 1 }}>heatML • обзор</p>
        <h2 style={{ margin: 0 }}>Добро пожаловать</h2>
        <p style={{ color: 'var(--color-text-muted)', maxWidth: 520 }}>
          Загрузите три CSV (характеристики домов, потребление, температура), дождитесь подготовки, запустите прогноз
          и заберите PDF-отчёт. Ниже быстрые ссылки на основные разделы.
        </p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button type="button" className="primary" onClick={() => navigate('/datasets')}>
            К датасетам
          </button>
          <button type="button" className="primary" onClick={() => navigate('/forecasts')}>
            Перейти к прогнозам
          </button>
          <button type="button" className="primary" onClick={() => navigate('/reports')}>
            Отчёты качества
          </button>
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        {stats.map((item) => (
          <div key={item.label} className="card" style={{ padding: 16 }}>
            <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>{item.label}</p>
            <h3 style={{ margin: '6px 0 0', fontSize: 28 }}>{item.value}</h3>
          </div>
        ))}
      </section>
    </div>
  );
};

export default OverviewPage;
