import { FormEvent, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthAPI } from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import styles from './LoginPage.module.css';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await AuthAPI.register(form.email, form.password);
      const { data } = await AuthAPI.login(form.email, form.password);
      login(data.access_token, data.refresh_token);
      navigate('/datasets');
    } catch (err) {
      setError('Не удалось зарегистрироваться, проверьте данные');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h2>Регистрация</h2>
        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </label>
        <label>
          Пароль (мин. 8 символов, буквы+цифры/символы)
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </label>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" className="primary" disabled={loading}>
          {loading ? 'Создаю…' : 'Создать аккаунт'}
        </button>
        <p style={{ color: 'var(--color-text-muted)', margin: '8px 0 0' }}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  );
};

export default RegisterPage;
