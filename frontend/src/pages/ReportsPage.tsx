import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ReportsAPI } from '../lib/api';

const ReportsPage = () => {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const response = await ReportsAPI.list();
      return response.data.items ?? [];
    },
  });

  return (
    <section className="card">
      <h2>Отчёты о качестве данных</h2>
      {isLoading ? (
        <p>Загрузка отчётов…</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Датасет</th>
              <th>Создан</th>
              <th>Метрик</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.map((item: any) => (
              <tr key={item.id}>
                <td>{item.batch_id}</td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
                <td>{Object.keys(item.metrics || {}).length}</td>
                <td>
                  <button type="button" className="primary" onClick={() => navigate(`/reports/${item.batch_id}`)}>
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

export default ReportsPage;
