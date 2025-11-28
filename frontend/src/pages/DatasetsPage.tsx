import { useState } from 'react';
import type { CSSProperties } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DatasetAPI, ForecastAPI } from '../lib/api';

const FILE_TYPES = [
  { key: 'house_features', label: 'Характеристики домов' },
  { key: 'consumption', label: 'Потребление' },
  { key: 'temperature', label: 'Температура' },
];

const formatDate = (value?: string) => {
  if (!value) return '—';
  return new Date(value).toLocaleString();
};

const pillStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  padding: '4px 10px',
  borderRadius: 999,
  border: '1px solid var(--color-border)',
  background: 'rgba(255,255,255,0.04)',
  fontSize: 12,
};

const DatasetsPage = () => {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => {
      const response = await DatasetAPI.list();
      return response.data.items ?? [];
    },
  });

  const createDataset = useMutation({
    mutationFn: (payload: { name: string }) => DatasetAPI.create(payload.name),
    onSuccess: () => {
      setName('');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: () => setError('Не удалось создать датасет'),
  });

  const uploadFile = useMutation({
    mutationFn: (payload: { batchId: string; fileType: string; file: File }) =>
      DatasetAPI.uploadFile(payload.batchId, payload.fileType, payload.file),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: () => setError('Не удалось загрузить файл (проверьте CSV)'),
  });

  const startForecast = useMutation({
    mutationFn: (payload: { batchId: string }) => ForecastAPI.create(payload.batchId),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['forecasts'] });
    },
    onError: () => setError('Не удалось запустить прогноз'),
  });

  const handleUpload = (batchId: string, fileType: string, fileList: FileList | null) => {
    if (!fileList?.length) return;
    uploadFile.mutate({ batchId, fileType, file: fileList[0] });
  };

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section className="card" style={{ display: 'grid', gap: 12 }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0 }}>Датасеты</h2>
            <p style={{ color: 'var(--color-text-muted)', margin: 0 }}>Создайте набор и загрузите три CSV</p>
          </div>
          <button type="button" className="primary" onClick={() => refetch()}>
            Обновить список
          </button>
        </header>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <input
            placeholder="Название набора данных"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ maxWidth: 300 }}
          />
          <button
            type="button"
            className="primary"
            onClick={() => createDataset.mutate({ name })}
            disabled={!name || createDataset.isPending}
          >
            {createDataset.isPending ? 'Создаю…' : 'Создать набор'}
          </button>
        </div>
        {error && <p style={{ color: '#fda29b' }}>{error}</p>}
      </section>

      {isLoading ? (
        <p>Loading…</p>
      ) : (
        data?.map((batch: any) => (
          <section key={batch.id} className="card" style={{ display: 'grid', gap: 12 }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>{batch.id}</p>
                <h3 style={{ margin: 0 }}>{batch.name}</h3>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={pillStyle}>{batch.status}</span>
                <span style={pillStyle}>Создан: {formatDate(batch.created_at)}</span>
              </div>
            </header>

            <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
              {FILE_TYPES.map((type) => {
                const file = batch.files?.find((f: any) => f.file_type === type.key);
                return (
                  <label
                    key={type.key}
                    className="card"
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      borderStyle: 'dashed',
                      borderWidth: 1,
                      cursor: 'pointer',
                      display: 'grid',
                      gap: 6,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>{type.label}</strong>
                      <span style={{ ...pillStyle, background: 'rgba(104, 188, 131, 0.12)' }}>
                        {file ? file.status : 'не загружен'}
                      </span>
                    </div>
                    <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 13 }}>
                      {file ? file.filename : 'Файл CSV; разделитель ";"'}
                    </p>
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      onChange={(e) => {
                        handleUpload(batch.id, type.key, e.target.files);
                        e.target.value = '';
                      }}
                    />
                  </label>
                );
              })}
            </div>

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                type="button"
                className="primary"
                disabled={batch.status !== 'prepared' || startForecast.isPending}
                onClick={() => startForecast.mutate({ batchId: batch.id })}
              >
                {startForecast.isPending ? 'Запускаю…' : 'Запустить прогноз'}
              </button>
              <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                Нужен статус prepared и готовый датасет. Прогноз появится в разделе «Прогнозы».
              </p>
            </div>
          </section>
        ))
      )}
    </div>
  );
};

export default DatasetsPage;
