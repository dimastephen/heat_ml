import { useAuth } from '../hooks/useAuth';
import styles from './TopBar.module.css';

interface Props {
  breadcrumbs: string[];
}

const TopBar: React.FC<Props> = ({ breadcrumbs }) => {
  const { logout } = useAuth();
  const path = breadcrumbs.length ? breadcrumbs.join(' / ') : 'overview';

  return (
    <header className={styles.header}>
      <div>
        <p className={styles.caption}>Текущий раздел</p>
        <h1 className={styles.title}>{path}</h1>
      </div>
      <button type="button" className="primary" onClick={logout}>
        Выйти
      </button>
    </header>
  );
};

export default TopBar;
