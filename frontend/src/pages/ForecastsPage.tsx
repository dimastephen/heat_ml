import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ForecastAPI } from '../lib/api';

const ForecastsPage = () => {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['forecasts'],
    queryFn: async () => {
      const response = await ForecastAPI.list();
      return response.data.items ?? [];
    },
  });

  return (
    <section className="card">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Прогнозы</h2>
          <p style={{ color: 'var(--color-text-muted)' }}>Отслеживайте статус и открывайте детали</p>
        </div>
      </header>
      {isLoading ? (
        <p>Загрузка прогнозов…</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Статус</th>
              <th>Метрики</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.map((job: any) => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.status}</td>
                <td>
                  {Object.entries(job.metrics || {}).map(([key, value]) => (
                    <span key={key} style={{ marginRight: 12 }}>
                      {key}: {JSON.stringify(value)}
                    </span>
                  ))}
                </td>
                <td>
                  <button type="button" className="primary" onClick={() => navigate(`/forecasts/${job.id}`)}>
                    Открыть
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
};

export default ForecastsPage;
