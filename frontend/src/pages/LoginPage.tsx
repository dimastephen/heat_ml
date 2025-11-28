import { FormEvent, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthAPI } from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import styles from './LoginPage.module.css';

const LoginPage = () => {
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
      const { data } = await AuthAPI.login(form.email, form.password);
      login(data.access_token, data.refresh_token);
      navigate('/datasets');
    } catch (err) {
      setError('Failed to login, please check credentials');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h2>Sign in</h2>
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
          Password
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </label>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" className="primary" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <p style={{ color: 'var(--color-text-muted)', margin: '8px 0 0' }}>
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  );
};

export default LoginPage;
