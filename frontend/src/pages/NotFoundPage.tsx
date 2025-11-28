import { Link } from 'react-router-dom';

const NotFoundPage = () => (
  <section className="card">
    <h2>404</h2>
    <p>Page not found.</p>
    <Link to="/">Go home</Link>
  </section>
);

export default NotFoundPage;
