import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ForecastAPI } from '../lib/api';

const ForecastDetailsPage = () => {
  const { jobId } = useParams();
  const [selectedHouse, setSelectedHouse] = useState<string | null>(null);

  const jobQuery = useQuery({
    queryKey: ['forecast', jobId],
    queryFn: async () => {
      const response = await ForecastAPI.get(jobId!);
      return response.data;
    },
    enabled: Boolean(jobId),
  });

  const houseListQuery = useQuery({
    queryKey: ['forecast-houses', jobId],
    queryFn: async () => {
      const response = await ForecastAPI.listHouses(jobId!);
      return response.data.items ?? [];
    },
    enabled: Boolean(jobId),
  });

  const houseSeriesQuery = useQuery({
    queryKey: ['forecast-house-series', jobId, selectedHouse],
    queryFn: async () => {
      const response = await ForecastAPI.getHouseSeries(jobId!, selectedHouse!);
      return response.data.points ?? [];
    },
    enabled: Boolean(jobId && selectedHouse),
  });

  const selectedHouseMetrics = useMemo(() =>
    houseListQuery.data?.find((item: any) => item.house_id === selectedHouse),
  [houseListQuery.data, selectedHouse]);

  if (!jobId) {
    return <p>Не указан идентификатор прогноза</p>;
  }

  return (
    <div className="card" style={{ display: 'grid', gap: 24 }}>
      <header>
        <h2>Прогноз #{jobId}</h2>
        <p style={{ color: 'var(--color-text-muted)' }}>статус: {jobQuery.data?.status}</p>
      </header>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {houseListQuery.data?.map((house: any) => (
          <button
            key={house.house_id}
            type="button"
            className="primary"
            style={{ background: selectedHouse === house.house_id ? 'var(--color-primary)' : 'transparent', color: selectedHouse === house.house_id ? '#04110a' : 'var(--color-text)', border: '1px solid var(--color-border)', padding: '8px 12px' }}
            onClick={() => setSelectedHouse(house.house_id)}
          >
            {house.house_id}
          </button>
        ))}
      </div>

      {selectedHouse && (
        <section>
          <h3>Дом {selectedHouse}</h3>
          {selectedHouseMetrics && (
            <p style={{ color: 'var(--color-text-muted)' }}>
              Суммарно {selectedHouseMetrics.total?.toFixed(2)}, среднее {selectedHouseMetrics.average?.toFixed(2)},
              пик {selectedHouseMetrics.peak?.toFixed(2)}
            </p>
          )}
          {houseSeriesQuery.isLoading ? (
            <p>Загрузка временного ряда…</p>
          ) : (
            <ul style={{ maxHeight: 240, overflow: 'auto' }}>
              {houseSeriesQuery.data?.map((point: any) => (
                <li key={point.timestamp}>
                  {new Date(point.timestamp).toLocaleDateString()} — {point.value.toFixed(2)}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div>
        <button
          type="button"
          className="primary"
          onClick={async () => {
            const { data } = await ForecastAPI.downloadReport(jobId);
            const blob = new Blob([data], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `forecast_${jobId}.pdf`;
            link.click();
            URL.revokeObjectURL(url);
          }}
        >
          Download PDF report
        </button>
      </div>
    </div>
  );
};

export default ForecastDetailsPage;
