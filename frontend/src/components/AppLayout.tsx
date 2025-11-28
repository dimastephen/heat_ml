import { Outlet, NavLink, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import styles from './AppLayout.module.css';

const navItems = [
  { label: 'Обзор', to: '/', end: true },
  { label: 'Датасеты', to: '/datasets' },
  { label: 'Прогнозы', to: '/forecasts' },
  { label: 'Отчёты', to: '/reports' },
];

const AppLayout = () => {
  const location = useLocation();

  return (
    <div className="app-shell">
      <Sidebar />
      <div className={styles.mainArea}>
        <TopBar breadcrumbs={location.pathname.split('/').filter(Boolean)} />
        <main>
          <nav className={styles.tabs}>
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? styles.activeTab : styles.tab)}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
