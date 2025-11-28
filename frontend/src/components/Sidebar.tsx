import { NavLink } from 'react-router-dom';

import styles from './Sidebar.module.css';

const Sidebar = () => {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>heatML</div>
      <div className={styles.sectionLabel}>Навигация</div>
      <NavLink to="/" end className={({ isActive }) => (isActive ? styles.active : styles.link)}>
        Обзор
      </NavLink>
      <NavLink to="/datasets" className={({ isActive }) => (isActive ? styles.active : styles.link)}>
        Датасеты
      </NavLink>
      <NavLink to="/forecasts" className={({ isActive }) => (isActive ? styles.active : styles.link)}>
        Прогнозы
      </NavLink>
      <NavLink to="/reports" className={({ isActive }) => (isActive ? styles.active : styles.link)}>
        Отчёты
      </NavLink>
    </aside>
  );
};

export default Sidebar;
